"""
Medicine detection for MediGuard AI.

The detector deliberately favors precision over recall. OCR text is matched
against known drug aliases, and fuzzy matching is limited to likely OCR
misspellings with a high similarity score.
"""

import re
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process


BASE_DIR = Path(__file__).resolve().parent
DRUG_DATASET_PATH = BASE_DIR / "data" / "drugs_side_effects_drugs_com.csv"
COMMON_DRUGS_PATH = BASE_DIR / "drugs.csv"
INTERACTION_DATASET_PATH = BASE_DIR / "data" / "db_drug_interactions.csv"

_drug_df = None
_alias_to_record = None
_single_word_aliases = None
_canonical_names = None

PACKAGING_WORDS = {
    "batch",
    "capsule",
    "capsules",
    "composition",
    "dosage",
    "dose",
    "expiry",
    "film",
    "manufactured",
    "manufacturer",
    "medicine",
    "prescription",
    "sodium",
    "strength",
    "tablet",
    "tablets",
}


def _normalize(value):
    text = str(value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _valid_alias(value):
    alias = _normalize(value)
    if len(alias) < 4 or len(alias) > 60:
        return False
    if alias in PACKAGING_WORDS:
        return False
    if len(alias.split()) > 5:
        return False
    if not re.search(r"[a-z]", alias):
        return False
    return True


def _record_score(record):
    useful_fields = (
        "side_effects",
        "drug_classes",
        "generic_name",
        "brand_names",
        "medical_condition",
    )
    return sum(bool(str(record.get(field, "")).strip()) for field in useful_fields)


def _empty_record(drug_name, source="interaction database"):
    return {
        "drug_name": str(drug_name).strip(),
        "generic_name": "",
        "brand_names": "",
        "drug_classes": "",
        "medical_condition": "",
        "side_effects": "",
        "pregnancy_category": "",
        "alcohol": "",
        "rating": "",
        "data_source": source,
    }


def _register_alias(alias_map, alias, record):
    normalized = _normalize(alias)
    if not _valid_alias(normalized):
        return

    existing = alias_map.get(normalized)
    new_is_canonical = normalized == _normalize(record.get("drug_name"))
    existing_is_canonical = (
        existing is not None
        and normalized == _normalize(existing.get("drug_name"))
    )
    if (
        existing is None
        or (new_is_canonical and not existing_is_canonical)
        or (
            new_is_canonical == existing_is_canonical
            and _record_score(record) > _record_score(existing)
        )
    ):
        alias_map[normalized] = record


def load_drug_database():
    global _drug_df, _alias_to_record, _single_word_aliases, _canonical_names

    if _drug_df is not None:
        return _drug_df

    df = pd.read_csv(DRUG_DATASET_PATH, low_memory=False).fillna("")
    df = df[df["drug_name"].map(_valid_alias)].copy()
    df["data_source"] = "drug information database"

    alias_map = {}
    canonical_records = {}

    for _, row in df.iterrows():
        record = row.to_dict()
        canonical = _normalize(record.get("drug_name"))
        if not canonical:
            continue

        current = canonical_records.get(canonical)
        if current is None or _record_score(record) > _record_score(current):
            canonical_records[canonical] = record

        _register_alias(alias_map, record.get("drug_name"), record)
        _register_alias(alias_map, record.get("generic_name"), record)
        for brand in str(record.get("brand_names", "")).split(","):
            _register_alias(alias_map, brand, record)

    if COMMON_DRUGS_PATH.exists():
        common_df = pd.read_csv(COMMON_DRUGS_PATH).fillna("")
        for _, row in common_df.iterrows():
            name = str(row.get("drug_name", "")).strip()
            canonical = _normalize(name)
            if not _valid_alias(name):
                continue

            record = canonical_records.get(canonical, _empty_record(name, "common drugs database")).copy()
            record["generic_name"] = record.get("generic_name") or row.get("generic_name", "")
            record["drug_classes"] = record.get("drug_classes") or row.get("category", "")
            record["side_effects"] = record.get("side_effects") or row.get("side_effects", "")
            record["warnings"] = row.get("warnings", "")
            record["common_dosage"] = row.get("common_dosage", "")
            canonical_records[canonical] = record
            _register_alias(alias_map, name, record)
            _register_alias(alias_map, row.get("generic_name"), record)

    # The interaction database expands recognition coverage for drugs that are
    # missing from the descriptive dataset, without inventing medicine details.
    if INTERACTION_DATASET_PATH.exists():
        interaction_df = pd.read_csv(
            INTERACTION_DATASET_PATH,
            usecols=["Drug 1", "Drug 2"],
        ).fillna("")
        for column in ("Drug 1", "Drug 2"):
            for name in interaction_df[column].drop_duplicates():
                canonical = _normalize(name)
                if not _valid_alias(name):
                    continue
                record = canonical_records.get(canonical, _empty_record(name))
                canonical_records.setdefault(canonical, record)
                _register_alias(alias_map, name, record)

    _drug_df = df
    _alias_to_record = alias_map
    _single_word_aliases = sorted(
        alias for alias in alias_map if " " not in alias and len(alias) >= 5
    )
    _canonical_names = sorted(
        {
            str(record.get("drug_name", "")).strip()
            for record in canonical_records.values()
            if str(record.get("drug_name", "")).strip()
        },
        key=str.lower,
    )
    return _drug_df


def get_all_drug_names():
    load_drug_database()
    return sorted(_alias_to_record)


def get_canonical_drug_names():
    load_drug_database()
    return _canonical_names


def find_drug_record(matched_name):
    load_drug_database()
    record = _alias_to_record.get(_normalize(matched_name))
    return record.copy() if record else None


def _add_detection(detected, seen, alias, matched_text, match_type, confidence):
    record = _alias_to_record.get(alias)
    if not record:
        return

    key = _normalize(record.get("drug_name"))
    if not key or key in seen:
        return

    result = record.copy()
    result["matched_text"] = matched_text
    result["matched_alias"] = alias
    result["match_type"] = match_type
    result["match_confidence"] = round(float(confidence), 1)
    detected.append(result)
    seen.add(key)


def detect_medicines(ocr_text):
    """Return high-confidence medicine records detected in OCR text."""
    load_drug_database()

    normalized_text = _normalize(ocr_text)
    if not normalized_text:
        return []

    detected = []
    seen = set()

    # Exact phrase matching is the safest signal and also supports multi-word
    # drug names. Longer aliases are checked first.
    exact_aliases = sorted(_alias_to_record, key=lambda item: (-len(item), item))
    for alias in exact_aliases:
        if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", normalized_text):
            _add_detection(detected, seen, alias, alias, "Exact", 100)

    # Fuzzy correction is restricted to individual OCR words. This catches
    # errors such as "pantoprizole" without matching normal package language.
    tokens = re.findall(r"[a-z][a-z0-9-]{4,}", normalized_text)
    for token in tokens:
        if token in PACKAGING_WORDS or token in _alias_to_record:
            continue

        match = process.extractOne(
            token,
            _single_word_aliases,
            scorer=fuzz.ratio,
            score_cutoff=88,
        )
        if not match:
            continue

        alias, score, _ = match
        length_gap = abs(len(token) - len(alias))
        required_score = 93 if min(len(token), len(alias)) <= 6 else 88
        if score < required_score or length_gap > 2:
            continue

        _add_detection(detected, seen, alias, token, "OCR correction", score)

    # Low-resolution packs sometimes produce a longer misspelling beside an
    # unmistakable dosage-form word. Permit a narrower fallback only when the
    # best match is clearly better than the runner-up.
    formulation_pattern = re.compile(
        r"\b(tab(?:let)?s?|cap(?:sule)?s?|injection|syrup)\b"
    )
    for raw_line in str(ocr_text).splitlines():
        line = _normalize(raw_line)
        if not formulation_pattern.search(line):
            continue

        for token in re.findall(r"[a-z][a-z0-9-]{8,}", line):
            if token in PACKAGING_WORDS:
                continue

            candidates = process.extract(
                token,
                _single_word_aliases,
                scorer=fuzz.ratio,
                limit=2,
            )
            if not candidates:
                continue

            alias, score, _ = candidates[0]
            runner_up = candidates[1][1] if len(candidates) > 1 else 0
            if (
                score >= 78
                and score - runner_up >= 8
                and abs(len(token) - len(alias)) <= 2
            ):
                _add_detection(
                    detected,
                    seen,
                    alias,
                    token,
                    "Contextual OCR correction",
                    score,
                )

    return sorted(detected, key=lambda item: str(item.get("drug_name", "")).lower())


def get_drug_names(detected):
    names = {
        str(drug.get("drug_name", "")).strip()
        for drug in detected
        if str(drug.get("drug_name", "")).strip()
    }
    return sorted(names, key=str.lower)


def get_drug_summary(drug_record):
    return {
        "Drug Name": drug_record.get("drug_name", ""),
        "Generic Name": drug_record.get("generic_name", ""),
        "Brand Name": drug_record.get("brand_names", ""),
        "Drug Class": drug_record.get("drug_classes", ""),
        "Medical Condition": drug_record.get("medical_condition", ""),
        "Side Effects": drug_record.get("side_effects", ""),
        "Warnings": drug_record.get("warnings", ""),
        "Pregnancy": drug_record.get("pregnancy_category", ""),
        "Alcohol": drug_record.get("alcohol", ""),
        "Rating": drug_record.get("rating", ""),
    }
