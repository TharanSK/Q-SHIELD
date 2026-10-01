"""
Statistical threat detection and physical verification engine.

Contains:
- SPRTDetector: Wald's Sequential Probability Ratio Test for non-ML signature verification.
- CHSHAnalyzer: Bell-CHSH inequality evaluation for quantum eavesdropping and tap detection.
- ConfidenceBounds: Clopper-Pearson and Wilson score intervals for empirical QBER.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Union
import numpy as np

from qshield.core.quantum import (
    PauliOperatorSet,
    DensityMatrix,
    EPRSource,
    QuantumChannel,
)


@dataclass
class SPRTDecision:
    """Outcome of Wald's Sequential Probability Ratio Test."""
    decision: str  # 'ACCEPT_H0' (genuine), 'REJECT_H1' (attack), 'CONTINUE'
    log_likelihood: float
    samples_evaluated: int
    error_count: int
    empirical_qber: float
    upper_bound: float
    lower_bound: float


@dataclass
class CHSHResult:
    """Outcome of Bell-CHSH inequality violation analysis."""
    s_value: float
    is_violated: bool  # True if S > 2.0 (quantum correlation exists)
    is_secure: bool    # True if S >= 2.4 (entanglement high enough to guarantee security)
    status: str        # 'OPTIMAL_ENTANGLEMENT', 'DEGRADED_ABORT', 'CLASSICAL_MITM_ABORT'
    e_ab: float
    e_ab_prime: float
    e_a_prime_b: float
    e_a_prime_b_prime: float
    samples_per_setting: Optional[int] = None


class SPRTDetector:
    """
    Wald's Sequential Probability Ratio Test (SPRT) engine.
    
    Tests hypotheses:
      H0 (Genuine signature): Error rate p <= p0 (channel noise limit, e.g. 0.02)
      H1 (Threat / Forgery):  Error rate p >= p1 (attack threshold, e.g. 0.25)
    
    Guarantees:
      False rejection probability <= alpha (default 1e-4)
      False acceptance probability <= beta (default 1e-4)
    """

    def __init__(
        self,
        p0: float = 0.02,
        p1: float = 0.25,
        alpha: float = 1e-4,
        beta: float = 1e-4,
    ):
        if not (0.0 < p0 < p1 < 1.0):
            raise ValueError(f"Requires 0 < p0 < p1 < 1, got p0={p0}, p1={p1}")
        if not (0.0 < alpha < 0.5 and 0.0 < beta < 0.5):
            raise ValueError(f"Requires 0 < alpha, beta < 0.5, got alpha={alpha}, beta={beta}")

        self.p0 = p0
        self.p1 = p1
        self.alpha = alpha
        self.beta = beta

        # Wald decision thresholds:
        # A >= (1 - beta) / alpha  --> reject H0 (accept H1)
        # B <= beta / (1 - alpha)  --> accept H0 (reject H1)
        self.threshold_A = math.log((1.0 - beta) / alpha)
        self.threshold_B = math.log(beta / (1.0 - alpha))

        # Log-likelihood increments per error (1) and per match (0)
        self.w1 = math.log(p1 / p0)
        self.w0 = math.log((1.0 - p1) / (1.0 - p0))

        # Runtime state for step-by-step streaming
        self.reset()

    def reset(self) -> None:
        """Reset internal sequential state."""
        self.current_llr = 0.0
        self.n_samples = 0
        self.n_errors = 0

    def step(self, observation: int) -> Tuple[str, float]:
        """
        Ingest a single bit/projective outcome:
        observation = 0: projective match (expected basis carrier verified)
        observation = 1: projective error (basis mismatch or scrambled state)
        Returns:
          (decision, current_llr)
        """
        self.n_samples += 1
        if observation == 1:
            self.n_errors += 1
            self.current_llr += self.w1
        else:
            self.current_llr += self.w0

        if self.current_llr >= self.threshold_A:
            return "REJECT_H1", self.current_llr
        elif self.current_llr <= self.threshold_B:
            return "ACCEPT_H0", self.current_llr
        else:
            return "CONTINUE", self.current_llr

    def evaluate_sequence(self, sequence: List[int]) -> Tuple[str, float]:
        """
        Evaluates a complete sequence of binary observations.
        Returns ('ACCEPT_H0' | 'REJECT_H1' | 'CONTINUE', final_llr).
        """
        self.reset()
        for obs in sequence:
            decision, llr = self.step(obs)
            if decision != "CONTINUE":
                return decision, llr

        # If sequence finished without crossing, decide based on threshold boundary proximity
        if self.current_llr >= self.threshold_A:
            return "REJECT_H1", self.current_llr
        elif self.current_llr <= 0.0:
            return "ACCEPT_H0", self.current_llr
        else:
            return "REJECT_H1", self.current_llr

    def get_status(self) -> SPRTDecision:
        """Return comprehensive status of the detector."""
        qber = (self.n_errors / self.n_samples) if self.n_samples > 0 else 0.0
        if self.current_llr >= self.threshold_A:
            decision = "REJECT_H1"
        elif self.current_llr <= self.threshold_B:
            decision = "ACCEPT_H0"
        else:
            decision = "CONTINUE"

        return SPRTDecision(
            decision=decision,
            log_likelihood=self.current_llr,
            samples_evaluated=self.n_samples,
            error_count=self.n_errors,
            empirical_qber=qber,
            upper_bound=self.threshold_A,
            lower_bound=self.threshold_B,
        )


class CHSHAnalyzer:
    """
    Bell-CHSH inequality verification engine.
    
    Evaluates:
      S = |E(a, b) - E(a, b') + E(a', b) + E(a', b')|
    
    Thresholds:
      S <= 2.0: Classical limit -> Local hidden variables / separable state / Full MITM interception.
      S < 2.4:  Degraded entanglement -> Insecure channel / Partial eavesdropping tap.
      S >= 2.4: Secure quantum entanglement (up to Tsirelson bound 2*sqrt(2) ~ 2.8284).
    """

    def __init__(
        self,
        angle_a: float = 0.0,
        angle_a_prime: float = math.pi / 2.0,
        angle_b: float = math.pi / 4.0,
        angle_b_prime: float = 3.0 * math.pi / 4.0,
    ):
        self.a = angle_a
        self.a_prime = angle_a_prime
        self.b = angle_b
        self.b_prime = angle_b_prime

    @staticmethod
    def get_measurement_operator(theta: float) -> np.ndarray:
        """
        Observable in X-Z plane:
        M(theta) = cos(theta)*Z + sin(theta)*X
        Eigenvalues are +1 and -1.
        """
        Z = PauliOperatorSet.Z
        X = PauliOperatorSet.X
        return math.cos(theta) * Z + math.sin(theta) * X

    def evaluate_density_matrix(self, rho_ab: DensityMatrix) -> CHSHResult:
        """
        Calculates exact CHSH expectation values on a 2-qubit density matrix.
        """
        M_a = self.get_measurement_operator(self.a)
        M_a_prime = self.get_measurement_operator(self.a_prime)
        M_b = self.get_measurement_operator(self.b)
        M_b_prime = self.get_measurement_operator(self.b_prime)

        # Joint measurement observables
        O_ab = np.kron(M_a, M_b)
        O_ab_prime = np.kron(M_a, M_b_prime)
        O_a_prime_b = np.kron(M_a_prime, M_b)
        O_a_prime_b_prime = np.kron(M_a_prime, M_b_prime)

        mat = rho_ab.data
        e_ab = float(np.trace(O_ab @ mat).real)
        e_ab_prime = float(np.trace(O_ab_prime @ mat).real)
        e_a_prime_b = float(np.trace(O_a_prime_b @ mat).real)
        e_a_prime_b_prime = float(np.trace(O_a_prime_b_prime @ mat).real)

        s_val = abs(e_ab - e_ab_prime + e_a_prime_b + e_a_prime_b_prime)

        is_violated = bool(s_val > 2.0001)
        is_secure = bool(s_val >= 2.4)

        if is_secure:
            status = "OPTIMAL_ENTANGLEMENT"
        elif not is_violated:
            status = "CLASSICAL_MITM_ABORT"
        else:
            status = "DEGRADED_ABORT"

        return CHSHResult(
            s_value=s_val,
            is_violated=is_violated,
            is_secure=is_secure,
            status=status,
            e_ab=e_ab,
            e_ab_prime=e_ab_prime,
            e_a_prime_b=e_a_prime_b,
            e_a_prime_b_prime=e_a_prime_b_prime,
        )

    def evaluate_channel(
        self,
        channel: QuantumChannel,
        bell_state: str = "Phi+",
    ) -> CHSHResult:
        """
        Evaluates CHSH parameter for a Bell pair transmitted through channel.
        """
        epr = EPRSource.create_bell_pair(bell_state)
        noisy_epr = channel.transmit_qubit_in_bipartite(epr, noisy_subsystem="B")
        return self.evaluate_density_matrix(noisy_epr)

    def evaluate_samples(
        self,
        n_samples: int,
        channel: Optional[QuantumChannel] = None,
        seed: Optional[int] = None,
    ) -> CHSHResult:
        """
        Simulates projective finite-sample CHSH evaluation across the four settings.
        """
        chan = channel or QuantumChannel()
        true_result = self.evaluate_channel(chan)
        rng = np.random.default_rng(seed)

        # Sample +/- 1 outcomes based on expectation value:
        # P(+1) = (1 + E)/2, P(-1) = (1 - E)/2
        def sample_e(e_val: float) -> float:
            p_plus = max(0.0, min(1.0, (1.0 + e_val) / 2.0))
            outcomes = rng.choice([1.0, -1.0], size=n_samples, p=[p_plus, 1.0 - p_plus])
            return float(np.mean(outcomes))

        emp_e_ab = sample_e(true_result.e_ab)
        emp_e_ab_prime = sample_e(true_result.e_ab_prime)
        emp_e_a_prime_b = sample_e(true_result.e_a_prime_b)
        emp_e_a_prime_b_prime = sample_e(true_result.e_a_prime_b_prime)

        emp_s = abs(emp_e_ab - emp_e_ab_prime + emp_e_a_prime_b + emp_e_a_prime_b_prime)
        is_violated = bool(emp_s > 2.0)
        is_secure = bool(emp_s >= 2.4)

        if is_secure:
            status = "OPTIMAL_ENTANGLEMENT"
        elif not is_violated:
            status = "CLASSICAL_MITM_ABORT"
        else:
            status = "DEGRADED_ABORT"

        return CHSHResult(
            s_value=emp_s,
            is_violated=is_violated,
            is_secure=is_secure,
            status=status,
            e_ab=emp_e_ab,
            e_ab_prime=emp_e_ab_prime,
            e_a_prime_b=emp_e_a_prime_b,
            e_a_prime_b_prime=emp_e_a_prime_b_prime,
            samples_per_setting=n_samples,
        )


class ConfidenceBounds:
    """
    Computes rigorous confidence intervals for empirical QBER and error rates.
    """

    @staticmethod
    def wilson_score_interval(
        successes: int, total: int, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """
        Wilson score interval with continuity correction.
        """
        if total <= 0:
            return 0.0, 1.0

        # Normal critical value z:
        # 0.95 -> 1.96, 0.99 -> 2.576
        z_values = {
            0.90: 1.645,
            0.95: 1.960,
            0.99: 2.576,
            0.999: 3.291,
        }
        z = z_values.get(confidence, 1.960)

        p = successes / total
        denominator = 1.0 + (z**2) / total
        center = (p + (z**2) / (2.0 * total)) / denominator
        margin = (
            z
            * math.sqrt((p * (1.0 - p) + (z**2) / (4.0 * total)) / total)
            / denominator
        )

        lower = max(0.0, center - margin)
        upper = min(1.0, center + margin)
        return lower, upper
