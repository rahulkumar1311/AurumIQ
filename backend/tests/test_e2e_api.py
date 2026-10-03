"""
End-to-End API Integration Verification Suite for AurumIQ
Uses FastAPI TestClient for robust, self-contained CI/CD execution.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_pipeline():
    # 1. Health
    res = client.get("/api/health")
    assert res.status_code == 200
    health = res.json()
    assert health["status"] == "healthy"

    # 2. Ingest Sample Data
    res = client.post("/api/data-quality/ingest-sample")
    assert res.status_code == 200
    ingest_res = res.json()
    assert ingest_res["records_loaded"] > 0

    # 3. Overview
    res = client.get("/api/overview")
    assert res.status_code == 200
    overview = res.json()
    assert len(overview["quotes"]) == 4

    # 4. Cross-Contract
    res = client.get("/api/cross-contract")
    assert res.status_code == 200
    cc = res.json()
    assert len(cc["history"]) > 0

    # 5. Spreads & Available Expiries
    res_exp = client.get("/api/expiries")
    assert res_exp.status_code == 200
    expiries = res_exp.json()["expiries"]
    assert "GOLDM" in expiries and len(expiries["GOLDM"]) > 0

    # Near-month test
    res = client.get("/api/spreads?pair_a=GOLDM&pair_b=GOLDPETAL&lookback=20&z_threshold=2.0")
    assert res.status_code == 200
    spreads = res.json()
    assert spreads["has_data"] is True
    st = spreads["statistics"]
    assert st["current_spread"] is not None
    assert "disclaimer" in spreads
    assert "ANALYTICAL INFORMATION ONLY" in spreads["disclaimer"]

    # Specific expiry test
    exp_a = expiries["GOLDM"][0]
    exp_b = expiries["GOLDPETAL"][0]
    res_spec = client.get(f"/api/spreads?pair_a=GOLDM&expiry_a={exp_a}&pair_b=GOLDPETAL&expiry_b={exp_b}&lookback=15")
    assert res_spec.status_code == 200
    spec_data = res_spec.json()
    assert spec_data["has_data"] is True
    assert len(spec_data["series"]) > 0

    # 6. Backtest
    payload = {
        "pair_a": "GOLDM",
        "pair_b": "GOLDPETAL",
        "entry_z": 1.5,
        "exit_z": 0.2,
        "stop_loss_z": 3.0,
        "lookback": 20,
        "initial_capital": 500000,
        "use_purity_adjusted": False,
        "include_friction": True
    }
    res = client.post("/api/backtest/run", json=payload)
    assert res.status_code == 200
    bt = res.json()
    assert bt["success"] is True
    assert bt["metrics"]["total_trades"] >= 0

    # 7. Data Quality & Calendar
    res = client.get("/api/data-quality")
    assert res.status_code == 200
    dq = res.json()
    assert dq["total_records"] > 0

    # 8. Reset to Empty State
    res = client.post("/api/data-quality/reset")
    assert res.status_code == 200
    reset_res = res.json()
    assert "reset" in reset_res["message"].lower()

    # 9. Verify Empty State restored
    res = client.get("/api/health")
    assert res.status_code == 200
    h2 = res.json()
    assert h2["has_data"] is False
    assert h2["total_market_records"] == 0

if __name__ == "__main__":
    test_full_pipeline()
    print("All E2E API tests passed successfully!")
