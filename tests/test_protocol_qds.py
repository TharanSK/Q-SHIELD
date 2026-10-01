"""
Sprint 2 Acceptance Tests: Protocol & Verifier.

Acceptance Gates:
- Deterministic signing and verification for legitimate signatures under channel noise e < 2%.
- Alice-Bob teleportation QDS signing pipeline.
- Decoy state basis selection (Z, X, Y MUBs).
- Epoch challenge nonce cache to prevent token reuse.
"""

import pytest
import numpy as np

from qshield.core.quantum import QuantumChannel, EPRSource
from qshield.protocol.qds import (
    SignerAlice,
    VerifierBob,
    TeleportationPipeline,
    EpochNonceCache,
    SignaturePackage,
)
from qshield.engine.stats import SPRTDetector


def test_epoch_nonce_cache_freshness_and_replay():
    """Verify monotonic epoch challenge nonce cache logic."""
    cache = EpochNonceCache(ttl_seconds=10.0)

    nonce1 = cache.generate_nonce()
    assert len(nonce1) == 64  # 32-byte hex

    # First consumption succeeds
    assert cache.is_valid_and_consume(nonce1, current_time=100.0) is True

    # Immediate replay is rejected
    assert cache.is_valid_and_consume(nonce1, current_time=101.0) is False

    # Second unique nonce succeeds
    nonce2 = cache.generate_nonce()
    assert cache.is_valid_and_consume(nonce2, current_time=102.0) is True

    # Expiration: nonce consumed at 100.0 expires after ttl_seconds=10.0
    cache._cleanup(now=115.0)
    assert nonce1 not in cache.consumed_nonces


def test_decoy_state_basis_selection():
    """Verify carrier states are distributed across MUBs (Z, X, Y) with decoy flags."""
    alice = SignerAlice(seed=42)
    carriers = alice.generate_carrier_states(length=300, decoy_ratio=0.5)

    bases = [c[1] for c in carriers]
    decoys = [c[3] for c in carriers]

    # Must contain all 3 bases
    assert set(bases) == {"Z", "X", "Y"}
    # Bases roughly uniformly distributed
    for b in ["Z", "X", "Y"]:
        assert bases.count(b) > 50

    # Decoy flags roughly 50%
    decoy_ratio = sum(decoys) / len(decoys)
    assert 0.35 < decoy_ratio < 0.65


def test_deterministic_qds_under_noise_gate():
    """
    SPRINT 2 ACCEPTANCE GATE:
    Deterministic signing and verification for legitimate signatures under
    channel noise e < 2%.
    """
    # 1.5% depolarizing channel noise (within e < 2% gate)
    noise_level = 0.015
    channel = QuantumChannel(depolarizing_prob=noise_level)
    pipeline = TeleportationPipeline(channel=channel, seed=123)

    sprt = SPRTDetector(p0=0.03, p1=0.25)

    # Test across multiple messages
    test_messages = [
        "TRANSACTION_HASH_#1001",
        "SMART_CONTRACT_STATE_ROOT",
        "INTERBANK_SETTLEMENT_ORDER",
    ]

    for msg in test_messages:
        pkg, result = pipeline.execute_protocol(
            message=msg,
            n_qubits=256,
            sprt_detector=sprt,
        )

        assert result.is_valid is True, f"Failed for message {msg}: {result.rejection_reason}"
        assert result.decision in ("ACCEPTED", "ACCEPT_H0")
        assert result.mean_fidelity > 0.95, f"Mean fidelity {result.mean_fidelity} too low"
        # Under 1.5% noise, QBER should be very low (typically 0% with 0.85 threshold)
        assert result.qber < 0.05, f"Empirical QBER {result.qber} exceeds tolerance"
