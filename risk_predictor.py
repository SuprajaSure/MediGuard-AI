"""Dataset-based medicine alert levels.

These levels summarize wording in the local side-effect dataset. They are not
personalized clinical risk predictions and are presented as such in the UI.
"""

from pathlib import Path
import re

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent


def _normalize(value):
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


class RiskPredictor:
    def __init__(self):
        self.risk_by_drug = {}
        self.trained = False

    def create_risk_label(self, side_effect_text):
        text = str(side_effect_text or "").lower()
        if not text.strip():
            return "Unknown"

        high_risk_keywords = (
            "call your doctor at once",
            "death",
            "heart attack",
            "kidney failure",
            "liver failure",
            "seizure",
            "coma",
            "stroke",
            "seek emergency medical",
            "trouble breathing",
        )
        if any(keyword in text for keyword in high_risk_keywords):
            return "High"

        effect_count = len(
            [part for part in re.split(r"[,;]", text) if part.strip()]
        )
        return "Medium" if effect_count >= 8 else "Low"

    def train(self, dataset_path=BASE_DIR / "data" / "drugs_side_effects_drugs_com.csv"):
        try:
            df = pd.read_csv(
                dataset_path,
                usecols=["drug_name", "generic_name", "side_effects"],
                low_memory=False,
            ).fillna("")

            severity_rank = {"Unknown": 0, "Low": 1, "Medium": 2, "High": 3}
            for _, row in df.iterrows():
                level = self.create_risk_label(row["side_effects"])
                for name in (row["drug_name"], row["generic_name"]):
                    key = _normalize(name)
                    if not key:
                        continue
                    current = self.risk_by_drug.get(key, "Unknown")
                    if severity_rank[level] > severity_rank[current]:
                        self.risk_by_drug[key] = level

            self.trained = True
            return True
        except Exception as exc:
            print("Risk data loading error:", exc)
            return False

    def predict_risk(self, drug_name, medical_condition=None):
        if not self.trained:
            return {
                "risk_level": "Unknown",
                "confidence": 0,
                "basis": "Risk dataset is unavailable.",
            }

        level = self.risk_by_drug.get(_normalize(drug_name), "Unknown")
        if level == "Unknown":
            return {
                "risk_level": "Unknown",
                "confidence": 0,
                "basis": "No side-effect record was found for this medicine.",
            }

        return {
            "risk_level": level,
            "confidence": 100,
            "basis": "Heuristic summary of the local side-effect dataset; not personalized risk.",
        }
