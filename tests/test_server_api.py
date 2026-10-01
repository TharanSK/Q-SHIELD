"""
Tests for FastAPI REST backend API endpoints in qshield.server.app.
"""

import pytest
from fastapi.testclient import TestClient

from qshield.server.app import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify /api/health endpoint."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_sign_and_verify_endpoint():
    """Verify /api/sign-and-verify endpoint."""
    payload = {
        "message": "TRANSACTION_TEST_PAYLOAD",
        "samples": 64,
        "noise": 0.01,
        "decoy_ratio": 0.5,
    }
    res = client.post("/api/sign-and-verify", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["is_valid"] is True
    assert data["decision"] in ("ACCEPTED", "ACCEPT_H0")
    assert data["mean_fidelity"] > 0.95
    assert data["total_qubits"] == 64
    assert len(data["nonce"]) == 64
    assert len(data["token_samples"]) > 0
    assert "fidelity_distribution" in data


def test_attack_simulation_endpoint():
    """Verify /api/attack endpoint across multiple threat vectors."""
    for attack in ["forgery", "impersonation", "replay", "mitm"]:
        payload = {
            "attack_type": attack,
            "samples": 64,
            "noise": 0.01,
        }
        res = client.post("/api/attack", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["detected"] is True
        assert len(data["detection_mechanism"]) > 0
        assert "telemetry" in data


def test_chsh_endpoint():
    """Verify /api/chsh endpoint under low and high noise."""
    # Low noise: secure
    res_clean = client.post("/api/chsh", json={"noise": 0.01})
    assert res_clean.status_code == 200
    data_clean = res_clean.json()
    assert data_clean["s_value"] > 2.4
    assert data_clean["is_secure"] is True
    assert data_clean["action"] == "PROCEED WITH PROTOCOL"

    # High noise: aborted
    res_noisy = client.post("/api/chsh", json={"noise": 0.25})
    assert res_noisy.status_code == 200
    data_noisy = res_noisy.json()
    assert data_noisy["is_secure"] is False
    assert data_noisy["action"] == "ABORT QUANTUM CHANNEL"


def test_benchmark_endpoint():
    """Verify /api/benchmark endpoint."""
    res = client.get("/api/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert data["throughput_qubits_per_sec"] > 5000.0
    assert data["false_acceptance_rate_far"] == 0.00
    assert "information_theoretic_bounds" in data
