# MediGuard AI

MediGuard AI is an educational medication-screening application built with
Streamlit. It reads prescription or medicine-pack images with OCR, identifies
likely medicine names, lets the user correct those names, checks known drug
interactions, and creates a styled PDF report.

## Current Features

- Upload and analyze multiple PNG, JPG, or JPEG images at once
- OCR extraction using EasyOCR and several image-enhancement variants
- Precision-focused medicine matching using exact aliases and guarded fuzzy matching
- Recognition of medicines contained only in the interaction database
- Manual medicine-name confirmation before interaction screening
- Pairwise drug-interaction checks across confirmed medicines
- Curated `HIGH`, `MODERATE`, and `LOW` interaction severity labels
- Honest `NOT CLASSIFIED` labels when the broad dataset has no severity value
- Dataset-derived side-effect alerts instead of misleading model probabilities
- Responsive Streamlit interface with accessible alert contrast
- Styled, downloadable PDF reports
- Regression tests for medicine detection, severity lookup, and PDF generation

## How It Works

1. The user uploads one or more medicine-pack or prescription images.
2. OpenCV creates original, enlarged, grayscale, and contrast-enhanced image variants.
3. EasyOCR extracts text from the variants.
4. The detector compares OCR text with known drug and brand aliases.
5. The user reviews and corrects the detected medicine names.
6. Every confirmed medicine pair is checked against the interaction datasets.
7. The app displays interaction severity and dataset-based side-effect alerts.
8. The reviewed results can be downloaded as a PDF report.

## Safety Notice

MediGuard AI is a final-year educational project, not a medical device and not
a replacement for a doctor or pharmacist.

- OCR can misread labels, especially in blurred or low-resolution images.
- A missing database result does not prove that a medicine combination is safe.
- Side-effect alert levels are dataset summaries, not personalized risk predictions.
- Never start, stop, combine, or change medication based only on this application.

## Technology

- Python
- Streamlit
- EasyOCR
- OpenCV
- PyTorch and TorchVision
- Pandas and NumPy
- RapidFuzz
- FPDF2
- Pillow

## Datasets

### `data/drugs_side_effects_drugs_com.csv`

Provides medicine names, generic names, brand aliases, drug classes, medical
conditions, side effects, pregnancy information, ratings, and related metadata.

### `data/db_drug_interactions.csv`

Provides broad drug-pair interaction descriptions. This dataset does not
contain severity labels, so matching records are shown as `NOT CLASSIFIED`.

### `interactions.csv`

Provides a smaller curated set of common interactions with:

- Drug 1
- Drug 2
- Severity
- Interaction type
- Description
- Suggested clinical action

## Installation

Python 3.13 is used by the current local environment.

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

EasyOCR downloads its recognition model the first time it is initialized, so
the first launch may take longer than later launches.

## Run The Application

```powershell
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

## Run Tests

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Project Structure

```text
MediGuard-AI/
|-- app.py
|-- medicine_detector.py
|-- ocr.py
|-- drug_interaction.py
|-- risk_predictor.py
|-- report_generator.py
|-- interactions.csv
|-- requirements.txt
|-- README.md
|-- data/
|   |-- db_drug_interactions.csv
|   `-- drugs_side_effects_drugs_com.csv
|-- tests/
|   `-- test_core.py
`-- uploads/
```

## Main Modules

- `app.py`: Streamlit interface and multi-image workflow
- `ocr.py`: image enhancement and OCR extraction
- `medicine_detector.py`: strict alias matching and OCR correction
- `drug_interaction.py`: structured interaction and severity lookup
- `risk_predictor.py`: dataset-derived side-effect alert labels
- `report_generator.py`: styled PDF report creation

## Known Limitations

- Very blurry labels can still require manual correction.
- The curated severity dataset covers fewer drug pairs than the broad dataset.
- Medicine information depends on the completeness of the bundled CSV files.
- The application does not consider dose, age, allergies, pregnancy, laboratory
  results, medical history, or other patient-specific clinical factors.

## Author

Supraja Sure  
B.Tech CSE (AIML)
