import html
import os
import tempfile

import streamlit as st

from drug_interaction import DrugInteractionChecker
from medicine_detector import (
    detect_medicines,
    find_drug_record,
    get_canonical_drug_names,
    get_drug_names,
)
from ocr import PrescriptionOCR
from report_generator import ReportGenerator
from risk_predictor import RiskPredictor


st.set_page_config(
    page_title="MediGuard AI",
    page_icon=":material/health_and_safety:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        :root {
            --ink: #183438;
            --muted: #60777b;
            --teal: #0d6974;
            --teal-dark: #114955;
            --mint: #e9f5f2;
            --line: #dbe8e7;
            --surface: #f7faf9;
        }
        .stApp {
            background:
                radial-gradient(circle at 85% 0%, rgba(44, 162, 153, .12), transparent 28rem),
                linear-gradient(180deg, #fbfdfc 0%, #f4f8f7 100%);
        }
        .block-container {
            max-width: 1180px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }
        .hero {
            padding: 2.1rem 2.3rem;
            border-radius: 24px;
            color: white;
            background: linear-gradient(125deg, #103f4b 0%, #0d6974 62%, #19887f 100%);
            box-shadow: 0 18px 45px rgba(15, 72, 80, .18);
            margin-bottom: 1.4rem;
        }
        .hero-kicker {
            font-size: .75rem;
            font-weight: 700;
            letter-spacing: .16em;
            text-transform: uppercase;
            opacity: .76;
        }
        .hero h1 {
            margin: .45rem 0 .35rem;
            font-size: clamp(2rem, 4vw, 3.4rem);
            letter-spacing: -.04em;
        }
        .hero p {
            max-width: 720px;
            margin: 0;
            color: rgba(255,255,255,.84);
            font-size: 1.04rem;
            line-height: 1.65;
        }
        .section-label {
            margin: 1.4rem 0 .65rem;
            color: var(--teal-dark);
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .medicine-card, .interaction-card, .empty-card {
            padding: 1.05rem 1.15rem;
            margin-bottom: .75rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.88);
            box-shadow: 0 8px 24px rgba(25, 65, 69, .06);
        }
        .medicine-card h3, .interaction-card h3 {
            margin: 0 0 .35rem;
            color: var(--ink);
            font-size: 1.05rem;
        }
        .medicine-card p, .interaction-card p, .empty-card {
            color: var(--muted);
            line-height: 1.55;
        }
        .meta {
            color: var(--muted);
            font-size: .86rem;
        }
        .severity {
            display: inline-block;
            padding: .25rem .6rem;
            margin-bottom: .55rem;
            border-radius: 999px;
            color: white;
            font-size: .72rem;
            font-weight: 800;
            letter-spacing: .06em;
        }
        .severity-high { background: #b52d37; }
        .severity-moderate { background: #c97b14; }
        .severity-low { background: #23875b; }
        .severity-not-classified { background: #66777b; }
        div[data-testid="stMetric"] {
            padding: 1rem 1.1rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,.78);
        }
        div[data-testid="stFileUploader"] {
            padding: .45rem;
            border-radius: 18px;
            background: rgba(255,255,255,.72);
        }
        .safety-note {
            padding: .9rem 1rem;
            border-left: 4px solid #cf8a21;
            border-radius: 8px;
            background: #fff7e7;
            color: #72501b;
            line-height: 1.55;
        }
        div[data-testid="stAlert"] {
            border-width: 1px;
            box-shadow: 0 5px 16px rgba(25, 65, 69, .05);
        }
        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] div {
            color: #24383c !important;
            opacity: 1 !important;
        }
        div[data-testid="stAlert"][data-baseweb="notification"] {
            color: #24383c !important;
        }
        div[data-testid="stAlert"] svg {
            color: #31565c !important;
            fill: currentColor !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def load_ocr():
    return PrescriptionOCR()


@st.cache_resource
def load_interaction_checker():
    return DrugInteractionChecker()


@st.cache_resource
def load_risk_predictor():
    predictor = RiskPredictor()
    predictor.train()
    return predictor


@st.cache_data
def load_drug_options():
    return get_canonical_drug_names()


def short_text(value, limit=360):
    text = " ".join(str(value or "").split())
    if not text:
        return "Not available in the local dataset."
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def analyze_uploads(uploaded_files):
    image_results = []
    record_map = {}

    for uploaded_file in uploaded_files:
        suffix = os.path.splitext(uploaded_file.name)[1] or ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(uploaded_file.getvalue())
            image_path = temp_file.name

        try:
            ocr_result = load_ocr().process_prescription(image_path)
            raw_text = ocr_result.get("raw_text", "")
            records = detect_medicines(raw_text)

            for record in records:
                name = str(record.get("drug_name", "")).strip()
                if name:
                    record_map[name.lower()] = record

            image_results.append(
                {
                    "name": uploaded_file.name,
                    "bytes": uploaded_file.getvalue(),
                    "raw_text": raw_text,
                    "records": records,
                }
            )
        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

    return {
        "images": image_results,
        "records": list(record_map.values()),
    }


ocr = load_ocr()
interaction_checker = load_interaction_checker()
risk_predictor = load_risk_predictor()
report_generator = ReportGenerator()

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Medication screening workspace</div>
        <h1>MediGuard AI</h1>
        <p>
            Upload one or more medicine-pack or prescription images. Review the
            detected names, compare interaction severity, and export a clear report.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="safety-note"><strong>Important:</strong> This project is a screening tool, '
    "not medical advice. Always confirm OCR results and ask a doctor or pharmacist "
    "before changing or combining medicines.</div>",
    unsafe_allow_html=True,
)

st.markdown('<div class="section-label">1. Add medicine images</div>', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Upload medicine packs or prescriptions",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Use clear, close-up images. You can upload separate images for separate medicines.",
    label_visibility="collapsed",
)

upload_col, action_col = st.columns([4, 1])
with upload_col:
    if uploaded_files:
        st.caption(f"{len(uploaded_files)} image(s) ready for analysis")
    else:
        st.caption("PNG, JPG, and JPEG files are supported.")
with action_col:
    analyze_clicked = st.button(
        "Analyze images",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    )

if analyze_clicked:
    with st.spinner("Reading labels and checking known medicine names..."):
        analysis = analyze_uploads(uploaded_files)
        st.session_state.analysis = analysis
        detected_names = get_drug_names(analysis["records"])
        st.session_state.reviewed_medicines = detected_names

analysis = st.session_state.get("analysis")

if analysis:
    st.markdown('<div class="section-label">2. Review image evidence</div>', unsafe_allow_html=True)
    image_columns = st.columns(min(3, len(analysis["images"])))
    for index, image_result in enumerate(analysis["images"]):
        with image_columns[index % len(image_columns)]:
            st.image(
                image_result["bytes"],
                caption=image_result["name"],
                use_container_width=True,
            )
            names = get_drug_names(image_result["records"])
            if names:
                st.caption("Detected: " + ", ".join(names))
            else:
                st.caption("No high-confidence medicine name detected")

    with st.expander("View OCR evidence"):
        for image_result in analysis["images"]:
            st.markdown(f"**{html.escape(image_result['name'])}**")
            st.code(image_result["raw_text"] or "No readable text extracted.", language=None)

    st.markdown('<div class="section-label">3. Confirm medicine names</div>', unsafe_allow_html=True)
    st.caption(
        "OCR can be wrong. Add or remove medicines here before trusting the interaction screen."
    )
    medicines = st.multiselect(
        "Confirmed medicines",
        options=load_drug_options(),
        key="reviewed_medicines",
        label_visibility="collapsed",
        placeholder="Search the medicine database",
    )

    confirmed_records = []
    detected_map = {
        str(record.get("drug_name", "")).lower(): record
        for record in analysis["records"]
    }
    for medicine in medicines:
        record = detected_map.get(medicine.lower()) or find_drug_record(medicine)
        if record:
            confirmed_records.append(record)

    interactions = interaction_checker.check_interactions(medicines)
    risk_results = []
    for medicine in medicines:
        result = risk_predictor.predict_risk(medicine)
        risk_results.append(
            {
                "drug": medicine,
                "risk": result["risk_level"],
                "confidence": result["confidence"],
                "basis": result["basis"],
            }
        )

    high_count = sum(item["severity"] == "HIGH" for item in interactions)
    classified_count = sum(item["severity"] != "NOT CLASSIFIED" for item in interactions)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Images analyzed", len(analysis["images"]))
    metric_columns[1].metric("Medicines confirmed", len(medicines))
    metric_columns[2].metric("Interactions listed", len(interactions))
    metric_columns[3].metric("High severity", high_count)

    st.markdown('<div class="section-label">Medicine summary</div>', unsafe_allow_html=True)
    if not medicines:
        st.markdown(
            '<div class="empty-card">No medicine is confirmed yet. Use the search box above '
            "to correct or add a medicine name.</div>",
            unsafe_allow_html=True,
        )

    for record in confirmed_records:
        name = html.escape(str(record.get("drug_name", "")))
        generic = html.escape(short_text(record.get("generic_name"), 120))
        drug_class = html.escape(short_text(record.get("drug_classes"), 160))
        condition = html.escape(short_text(record.get("medical_condition"), 160))
        side_effects = html.escape(short_text(record.get("side_effects"), 420))
        evidence = ""
        if record.get("match_type"):
            evidence = (
                f"<p class='meta'>Detection evidence: {html.escape(str(record.get('matched_text')))} "
                f"({html.escape(str(record.get('match_type')))}, "
                f"{record.get('match_confidence', 0)}%)</p>"
            )

        st.markdown(
            f"""
            <div class="medicine-card">
                <h3>{name}</h3>
                <p class="meta"><strong>Generic:</strong> {generic}<br>
                <strong>Class:</strong> {drug_class}<br>
                <strong>Dataset condition:</strong> {condition}</p>
                <p><strong>Side-effect summary:</strong> {side_effects}</p>
                {evidence}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-label">Interaction severity</div>', unsafe_allow_html=True)
    if len(medicines) < 2:
        st.info("Confirm at least two medicines to screen for pair interactions.")
    elif not interactions:
        st.success(
            "No listed interaction was found in the local databases. "
            "This does not prove the combination is safe."
        )

    for item in interactions:
        severity = item["severity"]
        severity_class = severity.lower().replace(" ", "-")
        st.markdown(
            f"""
            <div class="interaction-card">
                <span class="severity severity-{severity_class}">{html.escape(severity)}</span>
                <h3>{html.escape(str(item['drug_1']))} + {html.escape(str(item['drug_2']))}</h3>
                <p>{html.escape(str(item['description']))}</p>
                <p class="meta"><strong>Type:</strong> {html.escape(str(item['interaction_type']))}<br>
                <strong>Suggested action:</strong> {html.escape(str(item['clinical_action']))}<br>
                <strong>Source:</strong> {html.escape(str(item['source']))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if interactions and classified_count < len(interactions):
        st.caption(
            "Some interaction records have no severity label in their source dataset, "
            "so MediGuard leaves them as NOT CLASSIFIED instead of guessing."
        )

    st.markdown('<div class="section-label">Side-effect data alerts</div>', unsafe_allow_html=True)
    st.caption(
        "These are dataset-derived alert labels, not personalized predictions or probabilities."
    )
    for item in risk_results:
        level = item["risk"]
        if level == "High":
            st.error(f"{item['drug']}: high-alert wording appears in the side-effect dataset.")
        elif level == "Medium":
            st.warning(f"{item['drug']}: moderate side-effect data alert.")
        elif level == "Low":
            st.success(f"{item['drug']}: lower side-effect data alert.")
        else:
            st.info(f"{item['drug']}: no side-effect alert data available.")

    st.markdown('<div class="section-label">4. Export report</div>', unsafe_allow_html=True)
    if medicines:
        report_path = report_generator.generate_report(
            medicines=medicines,
            interactions=interactions,
            risk_results=risk_results,
            detected_records=confirmed_records,
            source_count=len(analysis["images"]),
        )
        try:
            with open(report_path, "rb") as report_file:
                report_bytes = report_file.read()
        finally:
            if os.path.exists(report_path):
                os.remove(report_path)

        st.download_button(
            "Download polished PDF report",
            data=report_bytes,
            file_name="MediGuard_Report.pdf",
            mime="application/pdf",
            type="primary",
        )

with st.sidebar:
    st.markdown("## How to use")
    st.write("1. Upload one or more clear medicine images.")
    st.write("2. Run the analysis.")
    st.write("3. Correct the detected medicine names.")
    st.write("4. Review interaction severity and export the report.")
    st.divider()
    st.markdown("### Detection policy")
    st.caption(
        "MediGuard now favors precision: exact database aliases and only "
        "high-confidence OCR corrections are accepted automatically."
    )
    st.divider()
    st.caption("Final Year Project\n\n23471A4255 | 23471A4229 | 23471A4219")
