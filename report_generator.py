"""Professional PDF report generation for MediGuard AI."""

from datetime import datetime
from pathlib import Path
import tempfile

from fpdf import FPDF


def _safe_text(value):
    text = str(value or "").replace("\u2192", "->")
    return text.encode("latin-1", "replace").decode("latin-1")


class MediGuardPDF(FPDF):
    def header(self):
        self.set_fill_color(17, 73, 85)
        self.rect(0, 0, 210, 28, "F")
        self.set_xy(15, 8)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 20)
        self.cell(0, 8, "MediGuard AI")
        self.set_xy(15, 17)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Medicine recognition and interaction screening report")
        self.ln(18)

    def footer(self):
        self.set_y(-13)
        self.set_text_color(100, 116, 120)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, f"Page {self.page_no()} | Screening support only", align="C")


class ReportGenerator:
    COLORS = {
        "HIGH": (181, 45, 55),
        "MODERATE": (202, 123, 20),
        "LOW": (35, 135, 91),
        "UNKNOWN": (92, 106, 112),
        "NOT CLASSIFIED": (92, 106, 112),
    }

    @staticmethod
    def _section_title(pdf, title):
        pdf.ln(3)
        pdf.set_text_color(17, 73, 85)
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 9, _safe_text(title), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(205, 219, 222)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)

    @staticmethod
    def _ensure_space(pdf, height):
        if pdf.get_y() + height > 274:
            pdf.add_page()

    def generate_report(
        self,
        medicines,
        interactions,
        risk_results,
        detected_records=None,
        source_count=0,
        output_file=None,
    ):
        if output_file is None:
            handle = tempfile.NamedTemporaryFile(
                prefix="MediGuard_Report_",
                suffix=".pdf",
                delete=False,
            )
            output_file = handle.name
            handle.close()

        pdf = MediGuardPDF()
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(15, 15, 15)
        pdf.add_page()

        pdf.set_text_color(45, 56, 60)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(
            0,
            6,
            _safe_text(datetime.now().strftime("Generated %d %B %Y at %I:%M %p")),
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)

        card_width = 56
        summaries = [
            ("Images", str(source_count)),
            ("Medicines", str(len(medicines))),
            ("Interactions", str(len(interactions))),
        ]
        start_x = 15
        y = pdf.get_y()
        for index, (label, value) in enumerate(summaries):
            x = start_x + index * 62
            pdf.set_fill_color(238, 245, 245)
            pdf.rect(x, y, card_width, 22, "F")
            pdf.set_xy(x + 4, y + 4)
            pdf.set_text_color(17, 73, 85)
            pdf.set_font("Helvetica", "B", 15)
            pdf.cell(card_width - 8, 7, value)
            pdf.set_xy(x + 4, y + 12)
            pdf.set_text_color(85, 102, 108)
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(card_width - 8, 5, label.upper())
        pdf.set_y(y + 27)

        self._section_title(pdf, "Detected medicines")
        record_map = {
            str(item.get("drug_name", "")).lower(): item
            for item in (detected_records or [])
        }
        if not medicines:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(
                0,
                6,
                "No medicines were confirmed.",
                new_x="LMARGIN",
                new_y="NEXT",
            )

        for medicine in medicines:
            self._ensure_space(pdf, 28)
            record = record_map.get(str(medicine).lower(), {})
            generic = record.get("generic_name") or "Not available in local data"
            drug_class = record.get("drug_classes") or "Not available in local data"

            pdf.set_fill_color(247, 249, 249)
            pdf.set_draw_color(220, 229, 230)
            x, y = pdf.get_x(), pdf.get_y()
            pdf.rect(x, y, 180, 24, "DF")
            pdf.set_xy(x + 5, y + 4)
            pdf.set_text_color(35, 48, 52)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(170, 6, _safe_text(medicine))
            pdf.set_xy(x + 5, y + 11)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(82, 98, 103)
            pdf.multi_cell(
                170,
                5,
                _safe_text(f"Generic: {generic} | Class: {drug_class}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_y(y + 28)

        self._section_title(pdf, "Interaction screening")
        if not interactions:
            pdf.set_fill_color(235, 247, 240)
            pdf.set_text_color(35, 110, 75)
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(
                0,
                7,
                "No listed interaction was found in the local databases. "
                "This does not prove the combination is safe.",
                fill=True,
                new_x="LMARGIN",
                new_y="NEXT",
            )

        for item in interactions:
            self._ensure_space(pdf, 42)
            severity = str(item.get("severity", "NOT CLASSIFIED")).upper()
            color = self.COLORS.get(severity, self.COLORS["UNKNOWN"])
            pdf.set_fill_color(*color)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(36, 7, _safe_text(severity), align="C")
            pdf.set_text_color(35, 48, 52)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(
                0,
                7,
                _safe_text(f"  {item.get('drug_1')} + {item.get('drug_2')}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(
                0,
                5,
                _safe_text(item.get("description")),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_text_color(75, 88, 92)
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(
                0,
                5,
                _safe_text(f"Suggested action: {item.get('clinical_action')}"),
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_text_color(35, 48, 52)
            pdf.ln(3)

        self._section_title(pdf, "Side-effect data alerts")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(82, 98, 103)
        pdf.multi_cell(
            0,
            5,
            "These labels summarize wording in the local side-effect dataset. "
            "They are not a personalized risk prediction.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)

        for item in risk_results:
            level = str(item.get("risk", "Unknown")).upper()
            color = self.COLORS.get(level, self.COLORS["UNKNOWN"])
            pdf.set_text_color(*color)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(36, 7, level, align="C", border=1)
            pdf.set_text_color(35, 48, 52)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(
                0,
                7,
                _safe_text(f"  {item.get('drug')}"),
                new_x="LMARGIN",
                new_y="NEXT",
                border=1,
            )

        self._section_title(pdf, "Important safety note")
        pdf.set_fill_color(255, 247, 226)
        pdf.set_text_color(92, 67, 19)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(
            0,
            6,
            "OCR can misread medicine labels, and the interaction databases are "
            "not exhaustive. Confirm every medicine name and consult a qualified "
            "doctor or pharmacist before changing, combining, or stopping medication.",
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.output(str(Path(output_file)))
        return str(output_file)
