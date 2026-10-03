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
