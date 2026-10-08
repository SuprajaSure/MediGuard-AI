"""Drug interaction lookup with explicit severity provenance."""

from itertools import combinations
from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent


def _normalize(value):
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


class DrugInteractionChecker:
    def __init__(
        self,
        curated_file=BASE_DIR / "interactions.csv",
        broad_file=BASE_DIR / "data" / "db_drug_interactions.csv",
    ):
        self.curated = pd.read_csv(curated_file).fillna("")
        self.broad = pd.read_csv(broad_file).fillna("")

        self.curated["_drug_1"] = self.curated["drug_1"].map(_normalize)
        self.curated["_drug_2"] = self.curated["drug_2"].map(_normalize)
        self.broad["_drug_1"] = self.broad["Drug 1"].map(_normalize)
        self.broad["_drug_2"] = self.broad["Drug 2"].map(_normalize)

    @staticmethod
    def _pair_matches(frame, first, second):
        return frame[
            ((frame["_drug_1"] == first) & (frame["_drug_2"] == second))
            | ((frame["_drug_1"] == second) & (frame["_drug_2"] == first))
        ]

    def check_interactions(self, medicines):
        interactions_found = []
        normalized = {
            _normalize(medicine): str(medicine).strip()
            for medicine in medicines
            if _normalize(medicine)
        }

        for first, second in combinations(sorted(normalized), 2):
            curated_matches = self._pair_matches(self.curated, first, second)
            if not curated_matches.empty:
                for _, row in curated_matches.iterrows():
                    interactions_found.append(
                        {
                            "drug_1": row["drug_1"],
                            "drug_2": row["drug_2"],
                            "severity": str(row["severity"]).upper(),
                            "interaction_type": row["interaction_type"],
                            "description": row["description"],
                            "clinical_action": row["clinical_action"],
                            "source": "curated severity database",
                        }
                    )
                continue

            broad_matches = self._pair_matches(self.broad, first, second)
            for _, row in broad_matches.drop_duplicates(
                subset=["Drug 1", "Drug 2", "Interaction Description"]
            ).iterrows():
                interactions_found.append(
                    {
                        "drug_1": row["Drug 1"],
                        "drug_2": row["Drug 2"],
                        "severity": "NOT CLASSIFIED",
                        "interaction_type": "Database-described interaction",
                        "description": row["Interaction Description"],
                        "clinical_action": "Ask a pharmacist or prescriber to assess clinical relevance.",
                        "source": "broad interaction database",
                    }
                )

        severity_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "NOT CLASSIFIED": 3}
        return sorted(
            interactions_found,
            key=lambda item: (
                severity_order.get(item["severity"], 4),
                item["drug_1"].lower(),
                item["drug_2"].lower(),
            ),
        )

    def get_interaction_count(self, medicines):
        return len(self.check_interactions(medicines))
