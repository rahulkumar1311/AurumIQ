# AurumIQ — Commodity Derivatives Intelligence

**Full-Stack Software Architecture for Hack in Hills Problem Statement #03: Commodity Derivatives Intelligence**

AurumIQ is an institutional-grade, light-theme quantitative analytics system built to analyze relative pricing differences, basis term structures, and defensible walk-forward statistical spread dynamics across Multi Commodity Exchange of India (MCX) Gold futures contracts: **GOLDM**, **GOLDTEN**, **GOLDGUINEA**, and **GOLDPETAL**.

---

## 🏛️ Project Architecture & Tech Stack

- **Frontend**: React 18, Vite, Recharts, Lucide-React, Pure Institutional Light CSS Design System.
- **Backend**: Python 3.12, FastAPI, Uvicorn (ASGI).
- **Quantitative Engine**: NumPy, Pandas, Chronological Walk-Forward Isolation (50% Dev / 25% Val / 25% Test), Parameter Freezing, Statutory Friction Engine (CTT, Stamp Duty, Brokerage, GST, SEBI & Illiquidity Surcharge), Point-in-Time Rolling Metrics (Zero Look-Ahead Bias), Augmented Dickey-Fuller (ADF) Stationarity, and Ornstein-Uhlenbeck Mean-Reversion Half-Life.
- **Storage**: SQLite with Write-Ahead Logging (WAL) mode and full Bhavcopy ingestion audit trail (`raw_bhavcopy_imports`, `raw_bhavcopy_records`, `validation_logs`).
- **Environment**: 100% Free local tools on Windows. Zero paid APIs, zero mandatory cloud services, zero fabricated prices, zero claims of live exchange execution or guaranteed profitability.

```
AurumIQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py             # FastAPI REST endpoints for all 5 modules
│   │   ├── backtesting/
│   │   │   └── engine.py             # Defensible walk-forward engine & benchmark alpha/beta
│   │   ├── config.py                 # MCX contract specs, lot sizes & statutory fees
│   │   ├── database/
│   │   │   └── connection.py         # SQLite schema, indices & connection pooling
│   │   ├── ingestion/
│   │   │   ├── mcx_downloader.py     # Automated MCX investigation client & WAF diagnostic
│   │   │   ├── mcx_parser.py         # MCX Bhavcopy CSV parser with date validation
│   │   │   ├── sample_data_loader.py # Authentic MCX historical feed loader
│   │   │   └── storage.py            # SQLite audit persistence & log tracking
│   │   ├── normalization/
│   │   │   └── normalizer.py         # Multiplier to 10g base & 999 fine gold equivalent
│   │   ├── signal/
│   │   │   └── spread_engine.py      # Point-in-time spreads, Z-scores, bands & O-U half-life
│   │   ├── validation/
│   │   │   └── validator.py          # OHLC integrity, tick bounds & outlier check
│   │   └── main.py                   # FastAPI application & lifespan setup
│   ├── data/
│   │   └── aurumiq.db                # Local SQLite database
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── mcx_bhavcopy_genuine_sample.csv # Genuine MCX Bhavcopy sample file
│   │   ├── test_aurumiq.py           # Core math, signal, backtesting & pipeline tests
│   │   ├── test_e2e_api.py           # Self-contained TestClient API integration test
│   │   ├── test_mcx_bhavcopy.py      # Bhavcopy parser, genuine file ingestion & date rejection
│   │   └── test_normalization_engine.py # Normalization invariance & multiplier matrix tests
│   ├── pytest.ini                    # Pytest configuration
│   └── requirements.txt              # Backend dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx            # Live health badge, date span & quick action controls
│   │   │   ├── EmptyState.jsx        # Institutional empty state with specs table
│   │   │   └── ErrorBoundary.jsx     # Global React error boundary protecting all views
│   │   ├── pages/
│   │   │   ├── OverviewDashboard.jsx        # Page 1: Live relative quotes, matrix & audit panel
│   │   │   ├── CrossContractComparison.jsx  # Page 2: Price trends, carry curve & liquidity
│   │   │   ├── HistoricalSpreadAnalysis.jsx # Page 3: Pair spreads, Z-scores & signal explanation
│   │   │   ├── BacktestingLab.jsx           # Page 4: Defensible walk-forward simulation lab
│   │   │   └── DataQualityCalendar.jsx      # Page 5: Pipeline health, ingestion engine & calendar
│   │   ├── App.jsx                   # Main layout & institutional tab bar
│   │   ├── index.css                 # Institutional light theme design system
│   │   └── main.jsx
│   ├── index.html                    # HTML shell with Inter typography
│   ├── package.json
│   └── vite.config.js                # Vite config with backend proxy (/api)
└── README.md
```

---

## 🏛️ Official MCX Gold Contract Specification Audit

**Verification Source**: [Official MCX India Bullion Product Specifications](https://www.mcxindia.com/products/bullion/gold) & MCX Circular MCX/TRD/714/2024  
**Date of Verification**: **October 4, 2026**

AurumIQ was audited against official Multi Commodity Exchange of India (MCX) contract specifications. All four contracts—**GOLDM**, **GOLDTEN**, **GOLDGUINEA**, and **GOLDPETAL**—are compulsory physical delivery futures traded on the MCX platform.

### Comprehensive Audit Matrix

| Contract | Trading Unit (Lot Size) | Quotation Unit (Price Quote) | Quotation Multiplier (to 10g) | Official MCX Purity (Fineness) | Problem Statement #03 Purity | Expiry Rule | Tender / Staggered Delivery Period | Physical Delivery Unit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GOLDM** | 100 grams | ₹ per 10 grams | **1.0x** | **995** | 995 | **5th day of expiry month** (or preceding business day if holiday) | Last 3 trading days of contract | 100g Bar |
| **GOLDTEN** | 10 grams | ₹ per 10 grams | **1.0x** | **999** (MCX/TRD/714/2024) | 999 | **Last calendar day of expiry month** (or preceding business day) | Last 3 trading days of contract | 10g Bar/Coin |
| **GOLDGUINEA**| 8 grams | ₹ per 8 grams | **1.25x** ($10/8$) | **995** (MCX Coin Standard) | **999** *(Flagged Assumption)* | **Last calendar day of expiry month** (or preceding business day) | Last 3 trading days of contract | 8g Coin |
| **GOLDPETAL** | 1 gram | ₹ per 1 gram | **10.0x** | **999** | 999 | **Last calendar day of expiry month** (or preceding business day) | Last 3 trading days of contract | 1g Blister Card |

---

### 🚩 Flagged Assumptions & Audit Discrepancies

1. **GOLDGUINEA Purity Discrepancy (Official MCX 995 vs. Hackathon Assumption 999)**:
   - **Official Exchange Finding**: The official MCX Gold Guinea product specification ([mcxindia.com/products/bullion/gold](https://www.mcxindia.com/products/bullion/gold)) explicitly defines the deliverable coin standard as **995 fineness** (99.5% pure gold).
   - **Problem Statement #03 Text**: Assigned GOLDGUINEA 999 purity.
   - **Resolution Without Guesswork**: AurumIQ makes this convention fully configurable via `NormalizationConfig(purity_convention=...)`:
     - Under `OFFICIAL_MCX` (default): GOLDGUINEA purity is 995.0, yielding a fine gold purity multiplier of $999 / 995 \approx 1.00402010$ and composite multiplier of $1.25 \times (999/995) \approx 1.255025$.
     - Under `PROBLEM_STATEMENT_03`: GOLDGUINEA purity is set to 999.0, yielding a purity multiplier of $1.000000$ and composite multiplier of $1.250000$.
     - The UI, normalization report, and API flag this discrepancy transparently with an `Audit Flag` badge.

2. **Expiry Cycle Asymmetry (5th of Month vs. Month-End)**:
   - **Official Rule**: `GOLDM` expires on the **5th day of the contract month**, whereas `GOLDTEN`, `GOLDGUINEA`, and `GOLDPETAL` expire on the **last calendar day of the contract month**.
   - **Cross-Contract Relative Value Impact**: Contracts labeled for the same month (e.g. October 2026) have an inherent maturity gap of ~25-26 calendar days (`2026-10-05` vs `2026-10-31`).
   - **Enforced Eligibility Rule**:
     - The engine detects this asymmetry and emits an explicit `Expiry Cycle Asymmetry` warning detailing the calendar gap and the financing carry adjustment.
     - Unsuitable expiry combinations where $|\text{DTE}_A - \text{DTE}_B| > 45\text{ days}$ are blocked from relative-value execution because calendar basis risk dominates product spread divergence.

3. **Compulsory Physical Delivery & Tender Window Constraints**:
   - **Official Rule**: All MCX gold futures are compulsory physical delivery contracts with a staggered tender period covering the **last 3 trading days** of the contract.
   - **Systematic Trading Safeguard**:
     - When either leg of a pair enters the tender window ($\text{DTE} \le 3\text{ days}$), the spread engine flags `IN_TENDER_PERIOD` and blocks actionable signal generation.
     - The backtesting engine enforces a mandatory tender buffer exit/roll prior to $\text{DTE} \le 3\text{ days}$ to ensure non-delivery compliance.

4. **Ground Truth Data Preservation**:
   - Original MCX Bhavcopy settlement prices (`close`, `open`, `high`, `low`, `volume`, `open_interest`) are strictly immutable and never overwritten in the database.

---

### Mathematical Normalization Invariance Principle
Quotation-unit differences alone do not generate spurious relative-value signals. When underlying physical gold trades at ₹7,500/g:
- GOLDM quoted at ₹75,000 / 10g → Normalized to ₹75,000 / 10g.
- GOLDGUINEA quoted at ₹60,000 / 8g → Normalized to ₹60,000 × (10/8) = ₹75,000 / 10g.
- GOLDPETAL quoted at ₹7,500 / 1g → Normalized to ₹7,500 × 10 = ₹75,000 / 10g.

---

## 🚀 Exact Windows Setup Commands

### Prerequisites
1. **Python 3.12+** (free from [python.org](https://www.python.org/))
2. **Node.js 18+ and npm** (free from [nodejs.org](https://nodejs.org/))
3. Windows PowerShell

### Step 1: Open PowerShell and Navigate to Workspace
```powershell
cd d:\AurumIQ
```

### Step 2: Backend Setup & Automated Test Verification
```powershell
cd d:\AurumIQ\backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements (if setting up fresh)
pip install -r requirements.txt

# Run all 72 automated backend tests
python -m pytest -v

# Start FastAPI backend server (http://127.0.0.1:8000)
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify backend health in a separate PowerShell tab:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" | ConvertTo-Json
```

### Step 3: Frontend Setup & Dev Server
In a new PowerShell terminal:
```powershell
cd d:\AurumIQ\frontend

# Install npm dependencies (if not already installed)
npm install

# Run Oxlint to verify code standards
npm run lint

# Build production bundle to verify zero syntax/build errors
npm run build

# Start Vite development server (http://localhost:5173)
npm run dev
```

Open your browser to: **[http://localhost:5173](http://localhost:5173)**

---

## ⚙️ Environment Variables & Configuration

AurumIQ is fully configured out of the box with zero required environment setup, but provides production flexibility via environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AURUMIQ_DB_PATH` | `data/aurumiq.db` | Absolute or relative path to SQLite database |
| `AURUMIQ_DATA_DIR` | `data` | Directory for database and import file staging |
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins (e.g. `http://localhost:5173,https://aurumiq.example.com`) |
| `PORT` | `8000` | Backend API listen port |

A sample template is provided in both root `.env.example` and `backend/.env.example`.

---

## 🚢 Deployment Requirements & Strategies

AurumIQ requires no paid third-party APIs or external subscription databases. It can be deployed in multiple production environments:

### Option A: Local Windows / Self-Hosted Production
1. **Backend**: Run with Uvicorn or Gunicorn with Uvicorn workers behind Nginx or Caddy:
   ```powershell
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
2. **Frontend**: Serve the production build (`frontend/dist`) using any static web server (Caddy, Nginx, or `serve`):
   ```powershell
   npx serve -s dist -l 5173
   ```
3. **Reverse Proxy**: Configure `/api` route forwarding to `http://127.0.0.1:8000/api`.

### Option B: Docker Containerization
 AurumIQ can be containerized using a multi-stage Dockerfile:
- **Backend Service**: Python 3.12-slim base image, installs `requirements.txt`, exposes port 8000 with SQLite volume mount at `/app/data`.
- **Frontend Service**: Node 20 base image, builds `dist`, served via Nginx alpine with proxy pass for `/api/`.

### Option C: Cloud Platform Deployment (e.g., Render / Railway / Fly.io + Vercel)
- **FastAPI Backend**: Deploy `backend/` to Render/Railway as a Web Service. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Attach a persistent volume to preserve `data/aurumiq.db`.
- **Vite Frontend**: Deploy `frontend/` to Vercel/Netlify. Configure build command: `npm run build`, output directory: `dist`, and set up URL rewrite rule to forward `/api/*` to the backend URL.

---

## 📥 Supported File Formats & Ingestion Pipeline

AurumIQ supports official daily MCX Bhavcopy reports exported from [https://www.mcxindia.com/market-data/bhavcopy](https://www.mcxindia.com/market-data/bhavcopy).

### 1. Supported File Formats:
- **File Extensions**: `.csv`, `.txt` (comma-delimited or semicolon-delimited). Maximum upload size: 25 MB.
- **Column Header Aliasing Supported**:
  - `symbol`: `Symbol`, `Commodity`, `Commodity_Name`, `Instrument_Name`, `Scrip`
  - `trade_date`: `Date`, `Trade_Date`, `TradeDate`, `Bhav_Date`, `Report_Date`
  - `expiry_date`: `ExpiryDate`, `Expiry_Date`, `Expiry`, `Exp_Date`, `Contract_Expiry`
  - `open`, `high`, `low`, `close`: `Open`, `High`, `Low`, `Close`, `Settlement_Price`, `Close_Price`
  - `volume`: `Volume`, `Traded_Qty`, `Volume_Lots`, `Total_Volume`, `Volume(Lots)`
  - `open_interest`: `OpenInterest`, `Open_Interest`, `OI`, `Total_OI`

### 2. Format Sanitization Capabilities:
- **Trailing & Leading Whitespace Stripping**: e.g., `"GOLDM   "` → `"GOLDM"`.
- **String Comma Cleansing**: e.g., `"75,280.00"` → `75280.0`.
- **Compact Expiry Date Parsing**: Handles `05OCT2026`, `05-OCT-2026`, `05/10/2026`, `2026-10-05`.
- **Date Ambiguity Disambiguation**: Handles files exported in US `MM/DD/YYYY` or Indian `DD/MM/YYYY`.
- **Duplicate Row Deduplication**: Gracefully detects, logs, and consolidates identical contract observations.

### 3. Date Mismatch Validation Enforcement:
- If a user requests or validates an import for date $D_{\text{req}}$ (e.g. `16/09/2026`), but the uploaded Bhavcopy file contains trading data for date $D_{\text{actual}}$ (e.g. `15/09/2026`), **the system strictly rejects the entire file**:
  ```json
  {
    "success": false,
    "status": "DATE_MISMATCH",
    "requested_date": "2026-09-16",
    "actual_data_date": "2026-09-15",
    "message": "Date mismatch: requested 16/09/2026 (2026-09-16), but MCX Bhavcopy file contains data for 2026-09-15. Silently treating older/different trading day data as requested date is strictly prohibited.",
    "records": []
  }
  ```
- **Audit Persistence**: Every attempt is recorded in SQLite tables `raw_bhavcopy_imports` and `validation_logs` with row counts and error reasons.

---

## 🔬 Defensible Walk-Forward Backtesting Engine

To eliminate data mining, backtest overfitting, and look-ahead bias, AurumIQ implements a rigorous walk-forward backtesting framework:

1. **Chronological 3-Way Partitioning (Zero Shuffling)**:
   - **Development Period (50%)**: Parameter calibration window.
   - **Validation Period (25%)**: Holdout verification window.
   - **Final Unseen Test Period (25%)**: True out-of-sample evaluation window.
   - Time-series observations are never randomly shuffled.
2. **Parameter Freezing**:
   - Model parameters (lookback window $L$, entry threshold $Z_{\text{entry}}$, exit threshold $Z_{\text{exit}}$, stop-loss $Z_{\text{stop}}$) are fitted strictly on the Development window and frozen before evaluating the Unseen Test window.
3. **Authentic Individual Contract Holdings**:
   - Strategy models actual individual contracts (e.g., `GOLDM_2026-10-05` and `GOLDPETAL_2026-09-30`), avoiding synthetic continuous front-month roll artifacts.
4. **Tender Notice Period Roll Buffer**:
   - Strategy automatically exits or rolls positions 3 trading days before contract expiry to avoid entering physical delivery tender periods under MCX delivery norms.
5. **Comprehensive Regulatory Friction Model**:
   - MCX Exchange Turnover Charge: $0.0015\%$
   - Commodity Transaction Tax (CTT): $0.01\%$ on sell turnover
   - Stamp Duty: $0.002\%$ on buy turnover
   - Brokerage: $0.005\%$
   - GST: $18\%$ on (Brokerage + Exchange Fees)
   - SEBI Regulatory Fee: ₹10 per crore turnover
   - Illiquidity Surcharge: Applied when daily volume $< 10$ lots.
6. **Benchmark Comparison**:
   - Strategy returns are compared side-by-side against an MCX Gold Buy & Hold benchmark, reporting **Alpha (% p.a.)**, **Beta**, **Correlation**, and **Information Ratio (IR)**.
7. **Downloadable Audit Reports**:
   - Walk-forward backtest results exportable to CSV via `/api/backtest/report`.
   - Normalization assumptions matrix exportable to CSV via `/api/normalization/report`.

---

## 🧪 Steps for Reproducing the Evaluation

To reproduce the evaluation and verify all system components:

### 1. Execute Automated Test Suite (72 Tests Across 6 Suites)
```powershell
cd d:\AurumIQ\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -v
```
All 72 tests pass:
- `tests/test_aurumiq.py` (25 tests): Core math, OHLC validation, point-in-time spreads, zero variance, outlier bounds, calendar gaps, walk-forward isolation, parameter freezing, and contract rolls.
- `tests/test_e2e_bhavcopy_audit.py` (17 tests): End-to-end Bhavcopy ingestion, persistence, date mismatch rejection, empty file handling, extension validation, insufficient history diagnostics, and direct download status auditing.
- `tests/test_mcx_bhavcopy.py` (13 tests): Date parsing, compact expiries, whitespace stripping, duplicate deduplication, genuine Bhavcopy file ingestion from disk, and date-mismatch rejection.
- `tests/test_mcx_spec_audit.py` (9 tests): Official MCX trading units, quotation units, purity conventions (OFFICIAL_MCX vs PROBLEM_STATEMENT_03), expiry rules, tender period constraints, and ground-truth exchange data preservation.
- `tests/test_normalization_engine.py` (7 tests): Mathematical invariance, quotation multiplier, purity conversion, and multiplier matrices.
- `tests/test_e2e_api.py` (1 test): Comprehensive self-contained API test across all endpoints.

### 2. Verify Date Mismatch Rejection
Run the explicit python verification script:
```powershell
& ".\.venv\Scripts\python.exe" -c "
from app.ingestion.mcx_parser import parse_mcx_bhavcopy_file
with open('tests/fixtures/mcx_bhavcopy_genuine_sample.csv', 'r') as f:
    res = parse_mcx_bhavcopy_file(f.read(), requested_date_str='22/09/2026')
assert res['success'] is False
assert res['status'] == 'DATE_MISMATCH'
print('Date Mismatch Rejection Verified: PASSED')
"
```

### 3. Verify Frontend Build & Visual UI
```powershell
cd d:\AurumIQ\frontend
npm run lint
npm run build
npm run dev
```
Navigate to `http://localhost:5173/`:
- **Overview Dashboard**: Inspect verified report date (`2026-09-18`), 4 normalized contract quotes, relative spread matrix, and the Normalization Multiplier Matrix.
- **Cross-Contract Comparison**: Inspect multi-contract normalized historical price trends, cost of carry term structure, and contract liquidity distribution.
- **Historical Spread Analysis**: Select Leg A and Leg B, configure lookback and Z-thresholds, and observe the 4 synchronized charts with Point-in-Time Z-scores, Bollinger Bands, and signal diagnostics.
- **Backtesting Lab**: Click "Execute Walk-Forward Backtest" and observe gross vs. net performance, out-of-sample multi-period breakdown, benchmark Alpha/Beta, equity curve partition boundaries, and download the CSV audit report.
- **Data Quality & Calendar**: Inspect pipeline health, active contract calendar with tender indicators, and audit log of imported Bhavcopy sessions.

---

## ⚠️ Known Limitations & Institutional Disclosures

1. **Direct Automated MCX Portal Download Block**:
   - Programmatic HTTP requests to `https://www.mcxindia.com/market-data/bhavcopy` are intercepted by MCX India's Web Application Firewall (WAF) or return dynamic ASP.NET ViewState forms, yielding HTTP 403 or non-CSV HTML responses.
   - AurumIQ explicitly recognizes and transparently logs this behavior (`FETCH_BLOCKED` or `DYNAMIC_PORTAL_INTERACTION_REQUIRED`) in the audit database. It does **not** fabricate fake downloads. The user-facing workflow is seamlessly supported through the Bhavcopy CSV upload endpoint (`/api/bhavcopy/upload`).
2. **Settlement Price vs. Executable Execution**:
   - Official MCX Bhavcopy reports publish daily closing and settlement prices (clearing marks determined by the exchange).
   - Settlement prices do not guarantee executable fill prices in real-time trading. Intraday execution is subject to order book depth, bid-ask spread slippage, and queue priority.
3. **Thin Contract Liquidity**:
   - Retail contracts like GOLDPETAL and GOLDGUINEA may experience periods of low trading volume relative to wholesale GOLDM. Frictions may be higher than estimated during stressed market conditions. AurumIQ includes an explicit illiquidity penalty in its statutory friction engine.
4. **Physical Delivery Tender Restrictions**:
   - MCX gold contracts enter a staggered physical delivery tender period in their final 3 trading days. Non-delivery participants must square off or roll positions prior to the tender window. AurumIQ blocks actionable signals and forces backtest rolls when $\text{DTE} \le 3$.
5. **No Claim of Live Market Access or Guaranteed Returns**:
   - AurumIQ does not claim live exchange connectivity, live broker API execution, or guaranteed trading profitability.
   - Historical backtesting metrics represent simulated mathematical evaluations under explicit cost assumptions and must not be interpreted as financial advice.
