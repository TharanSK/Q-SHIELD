"""
Sprint 4 Acceptance Tests: Evaluation & Packaging.

Acceptance Gates:
- Verification throughput > 5,000 qubit verifications/sec on standard CPU.
- False Acceptance Rate (FAR) = 0.00% under attacks.
- False Rejection Rate (FRR) < 0.10% under physical channel noise up to 3%.
- Security proof validation: undetected forgery leakage probability P < 10^-30 (N=256).
- Full benchmark report and acceptance gate verification.
"""

import pytest
import numpy as np

from qshield.bench.eval import (
    SecurityEvaluator,
    MetricsCollector,
    InformationTheoreticBound,
)
from qshield.cli.main import main


def test_throughput_acceptance_gate():
    """
    SPRINT 4 ACCEPTANCE GATE:
    Verification throughput > 5,000 qubit verifications/sec on standard CPU.
    """
    qps, latency_us = MetricsCollector.measure_verification_throughput(
        total_qubits=5000, batch_size=1000
    )
    assert qps > 5000.0, f"Verification throughput {qps:.1f} failed gate (> 5,000 qps)"
    assert latency_us < 200.0, f"Verification latency {latency_us:.2f} µs too high"


def test_information_theoretic_bound_proof_gate():
    """
    SPRINT 4 ACCEPTANCE GATE:
    Security proof validation: Undetected forgery leakage probability P < 10^-30.
    For N=256: P_undetected <= (0.75)^256 = 1.045 x 10^-32.
    """
    p_bound = InformationTheoreticBound.calculate_undetected_probability(256)
    assert p_bound <= 1.05e-32, f"Bound {p_bound} exceeds 1.05e-32"
    assert p_bound < 1e-30, f"Failed target P < 10^-30"

    min_n = InformationTheoreticBound.minimum_samples_for_target(1e-30)
    assert min_n <= 256, f"Minimum samples required ({min_n}) exceeds 256"


def test_security_evaluator_full_gates():
    """
    SPRINT 4 ACCEPTANCE GATE:
    FAR = 0.00%, FRR < 0.10% under 3% depolarizing noise, all gates passed.
    """
    evaluator = SecurityEvaluator(seed=777)
    report = evaluator.run_full_benchmark(
        n_attack_trials=20,
        n_genuine_trials=20,
        benchmark_qubits=2000,
    )

    assert report.false_acceptance_rate_far == 0.00, "FAR must be 0.00%"
    assert report.false_rejection_rate_frr < 0.01, f"FRR {report.false_rejection_rate_frr} too high"
    assert report.throughput_qubits_per_sec > 5000.0
    assert report.chsh_noiseless_s > 2.80
    assert report.chsh_classical_abort_s <= 2.0001
    assert report.passed_all_gates is True


def test_cli_subcommands_execution():
    """Verify all CLI entrypoint subcommands execute with exit code 0."""
    # Test verify
    assert main(["verify", "--samples", "64", "--noise", "0.01"]) == 0

    # Test chsh
    assert main(["chsh", "--noise", "0.01"]) == 0

    # Test attacks
    assert main(["attack", "--type", "forgery", "--samples", "64"]) == 0
    assert main(["attack", "--type", "impersonation", "--samples", "64"]) == 0
    assert main(["attack", "--type", "replay", "--samples", "64"]) == 0
    assert main(["attack", "--type", "mitm", "--samples", "64"]) == 0
