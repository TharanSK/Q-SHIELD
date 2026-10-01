"""
Sprint 3 Acceptance Tests: Threat Detection & SPRT.

Acceptance Gates:
- 100% detection of random forgery and replay attacks within N=256 test qubits.
- CHSH aborts when S <= 2.0 (classical limit) or S < 2.4 (degraded).
- SPRT sequential hypothesis decision engine (Wald test).
- Attack injection suite (Forgery, Replay, MITM Intercept-Resend).
"""

import pytest
import numpy as np

from qshield.core.quantum import QuantumChannel, EPRSource
from qshield.protocol.qds import TeleportationPipeline, VerifierBob
from qshield.engine.stats import SPRTDetector, CHSHAnalyzer
from qshield.attacks.sim import (
    ForgerySimulator,
    ReplayInjector,
    MITMInterception,
)


def test_sprt_engine_hypotheses_and_bounds():
    """Verify SPRT log-likelihood ratio accumulation and threshold crossing."""
    sprt = SPRTDetector(p0=0.02, p1=0.25, alpha=1e-4, beta=1e-4)

    assert sprt.threshold_A > 0.0
    assert sprt.threshold_B < 0.0

    # Clean sequence: 100 consecutive matches (0 errors)
    # Must cross lower threshold B (ACCEPT_H0)
    decision, llr = sprt.evaluate_sequence([0] * 100)
    assert decision == "ACCEPT_H0"
    assert llr <= sprt.threshold_B

    # Attack sequence: 50% error rate (forgery mismatch)
    # Must cross upper threshold A (REJECT_H1)
    attack_seq = [0, 1] * 50
    decision_att, llr_att = sprt.evaluate_sequence(attack_seq)
    assert decision_att == "REJECT_H1"
    assert llr_att >= sprt.threshold_A


def test_forgery_detection_acceptance_gate():
    """
    SPRINT 3 ACCEPTANCE GATE:
    100% detection of random forgery and impersonation attacks within N=256 test qubits.
    """
    forger = ForgerySimulator(seed=100)

    # 10 independent forgery trials
    for i in range(10):
        pipe = TeleportationPipeline(seed=200 + i)
        attack_res = forger.execute_forgery_attack(
            pipeline=pipe,
            message=f"FORGED_TX_{i}",
            n_qubits=256,
            tamper_ratio=1.0,
        )
        assert attack_res.detected is True, f"Forgery evaded detection in trial {i}"
        assert attack_res.metric_value >= 0.25, f"Expected QBER >= 25%, got {attack_res.metric_value}"

    # 10 independent impersonation trials
    for i in range(10):
        verifier = VerifierBob()
        imp_res = forger.execute_impersonation_attack(verifier, n_qubits=256)
        assert imp_res.detected is True, f"Impersonation evaded detection in trial {i}"
        # Mean fidelity must be ~0.50 (scrambled to I/2)
        assert imp_res.metric_value < 0.60


def test_replay_detection_acceptance_gate():
    """
    SPRINT 3 ACCEPTANCE GATE:
    100% detection of replay attacks within N=256 test qubits.
    Both Nonce Replay and Quantum Bell Monogamy Scrambling Replay.
    """
    replay = ReplayInjector(seed=300)

    # 1. Nonce reuse replay
    for i in range(5):
        pipe = TeleportationPipeline(seed=400 + i)
        r_nonce = replay.execute_nonce_replay(pipe, n_qubits=128)
        assert r_nonce.detected is True
        assert r_nonce.verification_result.decision == "REJECTED_REPLAY"

    # 2. Entanglement monogamy violation (replaying old classical tokens on fresh Bell pairs)
    for i in range(5):
        pipe = TeleportationPipeline(seed=500 + i)
        bell_pairs_old = EPRSource.create_batch(256, "Phi+")
        old_pkg, _ = pipe.alice.sign_message(f"OLD_CONTRACT_{i}", bell_pairs_old)

        fresh_bell = EPRSource.create_batch(256, "Phi+")
        r_mono = replay.execute_monogamy_scrambling_replay(pipe.bob, old_pkg, fresh_bell)

        assert r_mono.detected is True
        # Monogamy violation produces QBER >= 45%
        assert r_mono.metric_value >= 0.45, f"Expected QBER >= 45%, got {r_mono.metric_value}"


def test_chsh_mitm_abort_acceptance_gate():
    """
    SPRINT 3 ACCEPTANCE GATE:
    CHSH aborts when S <= 2.0 (classical limit) or S < 2.4.
    """
    mitm = MITMInterception(seed=600)

    # 1. Optimal unintercepted channel: S = 2*sqrt(2) ~ 2.8284
    clean_epr = EPRSource.create_bell_pair("Phi+")
    clean_res = mitm.chsh_analyzer.evaluate_density_matrix(clean_epr)
    assert clean_res.s_value > 2.80
    assert clean_res.is_violated is True
    assert clean_res.is_secure is True
    assert clean_res.status == "OPTIMAL_ENTANGLEMENT"

    # 2. Intercept-Resend attack: Entanglement collapsed to classical mixture
    # S = sqrt(2) ~ 1.4142 <= 2.0 -> Immediate abort
    ir_res = mitm.execute_mitm_attack("intercept_resend")
    assert ir_res.detected is True
    assert ir_res.metric_value <= 2.0001
    assert ir_res.chsh_result.status == "CLASSICAL_MITM_ABORT"

    # 3. Beam-splitting tap with 35% tap fraction -> Degraded below 2.4 -> Abort
    bs_res = mitm.execute_mitm_attack("beam_splitting")
    assert bs_res.detected is True
    assert bs_res.metric_value < 2.4
    assert bs_res.chsh_result.status in ("DEGRADED_ABORT", "CLASSICAL_MITM_ABORT")
