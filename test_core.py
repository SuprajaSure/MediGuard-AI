import tempfile
import unittest
from pathlib import Path

from drug_interaction import DrugInteractionChecker
from medicine_detector import detect_medicines, get_drug_names
from report_generator import ReportGenerator


class MedicineDetectorTests(unittest.TestCase):
    def test_packaging_words_do_not_become_medicines(self):
        records = detect_medicines(
            "Tablets capsules sodium batch expiry manufactured composition"
        )
        self.assertEqual(records, [])

    def test_exact_and_high_confidence_ocr_correction(self):
        records = detect_medicines("Pantoprizole tablets and aspirin")
        names = {name.lower() for name in get_drug_names(records)}
        self.assertIn("pantoprazole", names)
        self.assertIn("aspirin", names)

    def test_interaction_database_expands_drug_vocabulary(self):
        records = detect_medicines("Domperidone tablets")
        names = {name.lower() for name in get_drug_names(records)}
        self.assertIn("domperidone", names)

    def test_generic_name_is_preferred_over_brand_record(self):
        records = detect_medicines("Rabeprazole Sodium tablets")
        names = {name.lower() for name in get_drug_names(records)}
        self.assertIn("rabeprazole", names)

    def test_contextual_correction_for_low_resolution_pack(self):
        records = detect_medicines("Dormueridore (SR) Capsules")
        names = {name.lower() for name in get_drug_names(records)}
        self.assertIn("domperidone", names)


class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = DrugInteractionChecker()

    def test_curated_interaction_has_severity(self):
        result = self.checker.check_interactions(["Aspirin", "Warfarin"])
        self.assertTrue(result)
        self.assertEqual(result[0]["severity"], "HIGH")


class ReportTests(unittest.TestCase):
    def test_report_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.pdf"
            ReportGenerator().generate_report(
                medicines=["Aspirin", "Warfarin"],
                interactions=[
                    {
                        "drug_1": "Warfarin",
                        "drug_2": "Aspirin",
                        "severity": "HIGH",
                        "description": "Increased bleeding risk.",
                        "clinical_action": "Seek professional review.",
                    }
                ],
                risk_results=[
                    {"drug": "Aspirin", "risk": "High"},
                    {"drug": "Warfarin", "risk": "High"},
                ],
                source_count=2,
                output_file=output,
            )
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
