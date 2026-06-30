# 🚢 CargoPulse — Ship RFQ Analytics & PDF Extraction

CargoPulse is a [Streamlit](https://streamlit.io) + SQLite application that bulk-extracts
structured data from ship **RFQ / quotation PDFs**, stores it in a queryable database, and
turns it into analytics dashboards, per-entity analysis, and a formatted Excel export.

It understands three real-world maritime procurement formats out of the box and falls back to
an LLM (Claude / OpenAI) for unknown layouts.

---

## ✨ Features

- **Bulk PDF upload** with SHA-256 duplicate detection (identical files) and logical
  duplicate detection (same RFQ No + vessel + date).
- **Automatic format detection** for three formats, with format-specific parsers:
  - `SHIPSERV_RFQ` — ShipServ RFQ
  - `GARRETS_AMOS_QUOTATION` — Garrets / Amos quotation
  - `DANAOS_RFQ` — Danaos Shipping RFQ
- **AI fallback** (Claude or OpenAI) for unknown / difficult layouts — degrades gracefully
  to a review flag if no API key is configured.
- **Item category mapping** (Electrical, Galley, Safety, Deck, Cleaning/Cabin, Engine, …).
- **Validation** → review errors for missing RFQ/vessel/IMO/quantity/UoM, etc.
- **Dashboard** with KPI cards and charts (RFQs over time, top vessels/buyers/ports/items,
  quantity by category, format distribution).
- **Documents** & **Line Items** tables with filters, search, and CSV export.
- **Vessel / Item / Buyer / Port** analysis pages.
- **Review / Errors** page to inspect, filter and resolve extraction issues.
- **Excel export** — a formatted, multi-sheet workbook (Documents, Line_Items, four summaries,
  Review_Errors) with bold headers, frozen rows, auto-filters and column widths.
- **Settings** — initialize / clear / back up the database, choose the AI provider.

---

## 🧱 Tech stack

Python · Streamlit · SQLite · PyMuPDF · pdfplumber · pandas · openpyxl · Plotly ·
Anthropic & OpenAI SDKs.

---

## 🚀 Getting started

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) configure API keys for the AI fallback
#    Copy .env.example to .env and fill in the values.

# 4. Run the app
streamlit run app.py
```

Then open **http://localhost:8501**.

> On Windows, if `venv\Scripts\activate` is blocked by the execution policy, run the app
> directly with `venv\Scripts\python -m streamlit run app.py`.

---

## ⚙️ Configuration (`.env`)

| Variable            | Purpose                                                        |
| ------------------- | -------------------------------------------------------------- |
| `OPENAI_API_KEY`    | OpenAI key (optional — AI fallback only)                       |
| `ANTHROPIC_API_KEY` | Anthropic / Claude key (optional — AI fallback only)           |
| `AI_PROVIDER`       | `openai` · `claude` · `both` · `disabled`                      |
| `DATABASE_PATH`     | SQLite file location (default `data/vesseliq.sqlite`)          |

The real `.env` is git-ignored — never commit your API keys.

---

## 🗂️ Project structure

```
app.py                  # Streamlit entry point + sidebar router
app/                    # Page modules
  ├─ dashboard.py       # KPIs + charts
  ├─ upload.py          # Upload & process pipeline
  ├─ documents.py       # Documents table
  ├─ line_items.py      # Line items table
  ├─ analysis.py        # Vessel / Item / Buyer / Port analysis
  ├─ review.py          # Review / Errors
  ├─ export.py          # Excel export
  ├─ settings.py        # DB admin + AI provider
  ├─ components.py      # Shared UI helpers
  └─ public/            # Logo
modules/                # Business logic
  ├─ database.py        # SQLite schema + inserts + dedup helpers
  ├─ pdf_reader.py      # PyMuPDF text extraction
  ├─ format_detector.py # Format classification
  ├─ shipserv_parser.py / garrets_parser.py / danaos_parser.py
  ├─ category_mapper.py # Item → category
  ├─ validator.py       # Review-error generation
  ├─ processor.py       # End-to-end pipeline (hash → parse → validate → save → move)
  ├─ queries.py         # Analytics queries
  ├─ excel_exporter.py  # Multi-sheet formatted workbook
  ├─ ai_extractor.py    # Claude / OpenAI fallback
  ├─ schema.py          # Common document / line-item structures
  └─ utils.py           # Date / number / text helpers
data/                   # Working dirs (input/processed/failed PDFs, SQLite) — git-ignored
exports/                # Generated workbooks — git-ignored
```

---

## 🔄 Processing pipeline

```
Upload PDF
   └─ SHA-256 hash → skip if identical file already imported
   └─ Extract text (PyMuPDF) → flag scanned/empty PDFs
   └─ Detect format → ShipServ / Garrets / Danaos / Unknown
   └─ Parse (format-specific) or AI fallback for Unknown
   └─ Map categories + enrich line items
   └─ Validate → review errors
   └─ Logical duplicate check (RFQ + vessel + date)
   └─ Save to SQLite + move file to processed_pdfs/ (or failed_pdfs/)
```
