"""
Synthetic threat simulation harness for Q-SHIELD.

Implements attacks specified in the security specification:
- ForgerySimulator: Basis-unaware token generation and impersonation attacks.
- ReplayInjector: Nonce reuse and entanglement monogamy violation replay attacks.
- MITMInterception: Quantum channel intercept-resend and beam-splitting eavesdropping.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import numpy as np

from qshield.core.quantum import (
    PauliOperatorSet,
    DensityMatrix,
    EPRSource,
    QuantumChannel,
    state_fidelity,
)
from qshield.protocol.qds import (
    SignaturePackage,
    SignatureToken,
    VerifierBob,
    VerificationResult,
    SignerAlice,
    TeleportationPipeline,
)
from qshield.engine.stats import (
    SPRTDetector,
    CHSHAnalyzer,
    CHSHResult,
)


@dataclass
class AttackResult:
    """Outcome of simulated attack detection."""
    attack_type: str
    detected: bool
    detection_mechanism: str
    metric_value: float
    details: str
    verification_result: Optional[VerificationResult] = None
    chsh_result: Optional[CHSHResult] = None


class ForgerySimulator:
    """
    Simulates signature forgery and signer impersonation attacks.
    
    1. Signature Forgery: Adversary lacks private basis knowledge.
       Attempts to fabricate classical (b1, b2) tokens or carrier states.
       Basis mismatch creates conjugate projection error rate e >= 25%,
       triggering SPRT reject.
       
    2. Signer Impersonation: Adversary sends fake tokens (b1, b2).
       Pauli frame scrambling renders carrier state to maximally mixed
       rho = I/2, dropping projective fidelity to F = 0.50 (reject F < 0.85).
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def forge_tokens(
        self,
        original_tokens: List[SignatureToken],
        tamper_ratio: float = 1.0,
    ) -> List[SignatureToken]:
        """
        Adversary generates forged (b1, b2) tokens without private basis knowledge.
        Tampered tokens have random (b1, b2) values.
        """
        forged = []
        for tok in original_tokens:
            if self.rng.random() < tamper_ratio:
                # Randomly scramble (b1, b2)
                f_b1 = int(self.rng.integers(0, 2))
                f_b2 = int(self.rng.integers(0, 2))
                forged.append(
                    SignatureToken(
                        b1=f_b1,
                        b2=f_b2,
                        basis=tok.basis,
                        bit_value=tok.bit_value,
                        is_decoy=tok.is_decoy,
                    )
                )
            else:
                forged.append(tok)
        return forged

    def execute_forgery_attack(
        self,
        pipeline: TeleportationPipeline,
        message: str = "FORGED_MESSAGE",
        n_qubits: int = 256,
        tamper_ratio: float = 1.0,
    ) -> AttackResult:
        """
        Executes end-to-end forgery attack test.
        """
        # Step 1: Alice creates genuine distributed session
        bell_pairs = EPRSource.create_batch(n_qubits, "Phi+")
        package, raw_bob_qubits = pipeline.alice.sign_message(
            message=message,
            epr_pairs=bell_pairs,
        )

        # Step 2: Attacker intercepts and tampers with tokens
        forged_tokens = self.forge_tokens(package.tokens, tamper_ratio=tamper_ratio)
        tampered_pkg = SignaturePackage(
            message=package.message,
            tokens=forged_tokens,
            nonce=package.nonce,
            timestamp=package.timestamp,
        )

        # Step 3: Bob verifies with fresh SPRT detector
        sprt = SPRTDetector()
        res = pipeline.bob.verify_signature(
            package=tampered_pkg,
            bob_qubits=raw_bob_qubits,
            sprt_detector=sprt,
        )

        detected = (not res.is_valid) or (res.qber >= 0.25)
        details = (
            f"Forgery detected={detected}. QBER={res.qber:.2%} (expected >= 25%), "
            f"Mean Fidelity={res.mean_fidelity:.4f}, Decision={res.decision}"
        )

        return AttackResult(
            attack_type="SIGNATURE_FORGERY",
            detected=detected,
            detection_mechanism="SPRT_PROJECTIVE_MISMATCH",
            metric_value=res.qber,
            details=details,
            verification_result=res,
        )

    def execute_impersonation_attack(
        self,
        verifier: VerifierBob,
        n_qubits: int = 256,
    ) -> AttackResult:
        """
        Malicious actor transmits forged (b1, b2) tokens claiming Alice's identity
        while Bob receives uncorrelated or unentangled states.
        Pauli frame scrambling renders state to maximally mixed rho = I/2.
        Fidelity drops to F = 0.50 (reject F < 0.85).
        """
        tokens = []
        bases = ["Z", "X", "Y"]
        # Fake tokens generated by adversary
        for _ in range(n_qubits):
            tokens.append(
                SignatureToken(
                    b1=int(self.rng.integers(0, 2)),
                    b2=int(self.rng.integers(0, 2)),
                    basis=str(self.rng.choice(bases)),
                    bit_value=int(self.rng.integers(0, 2)),
                    is_decoy=True,
                )
            )

        # Uncorrelated random states received by Bob (e.g. maximally mixed or random pure)
        # Even if Bob receives I/2, projective fidelity against any pure state is Tr(P * I/2) = 0.50
        maximally_mixed = DensityMatrix(np.eye(2, dtype=complex) / 2.0)
        bob_qubits = [maximally_mixed for _ in range(n_qubits)]

        pkg = SignaturePackage(
            message="IMPERSONATED_PAYLOAD",
            tokens=tokens,
            nonce=verifier.nonce_cache.generate_nonce(),
        )

        sprt = SPRTDetector()
        res = verifier.verify_signature(pkg, bob_qubits, sprt_detector=sprt)

        detected = (not res.is_valid) or (res.mean_fidelity <= 0.55)
        details = (
            f"Impersonation detected={detected}. Mean Fidelity={res.mean_fidelity:.4f} "
            f"(expected ~0.50), QBER={res.qber:.2%}"
        )

        return AttackResult(
            attack_type="SIGNER_IMPERSONATION",
            detected=detected,
            detection_mechanism="PAULI_FRAME_SCRAMBLING_FIDELITY",
            metric_value=res.mean_fidelity,
            details=details,
            verification_result=res,
        )


class ReplayInjector:
    """
    Simulates replay attacks:
    1. Direct Nonce Replay: Adversary re-transmits valid previous teleportation
       classical bits (b1, b2) and identical nonce. Detected by Epoch Nonce Cache.
    2. Outdated Pauli Correction on Fresh Entanglement: Adversary bypasses nonce
       or re-transmits valid past (b1, b2) tokens against fresh distributed Bell pairs.
       Because entanglement is consumed per BSM, fresh Bell pairs are uncorrelated
       with the past BSM, scrambling the carrier state and yielding QBER >= 45%.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def execute_nonce_replay(
        self,
        pipeline: TeleportationPipeline,
        message: str = "ORIGINAL_CONTRACT",
        n_qubits: int = 128,
    ) -> AttackResult:
        """
        Adversary re-submits identical (b1, b2) package and nonce.
        First submission succeeds; second submission is rejected by Nonce Cache.
        """
        bell_pairs_1 = EPRSource.create_batch(n_qubits, "Phi+")
        pkg, raw_bob = pipeline.alice.sign_message(message, bell_pairs_1)

        # First verification (legitimate)
        res_legit = pipeline.bob.verify_signature(pkg, raw_bob)

        # Replay attempt with same package (same nonce)
        bell_pairs_fresh = EPRSource.create_batch(n_qubits, "Phi+")
        # Even with fresh Bob qubits
        fresh_bob = [pipeline.channel.apply_single_qubit_noise(q.partial_trace("A")) for q in bell_pairs_fresh]

        res_replay = pipeline.bob.verify_signature(pkg, fresh_bob)

        detected = (not res_replay.is_valid) and (res_replay.decision == "REJECTED_REPLAY")
        details = (
            f"Nonce Replay detected={detected}. Decision={res_replay.decision}, "
            f"Reason={res_replay.rejection_reason}"
        )

        return AttackResult(
            attack_type="REPLAY_NONCE_REUSE",
            detected=detected,
            detection_mechanism="EPOCH_NONCE_CACHE",
            metric_value=1.0 if detected else 0.0,
            details=details,
            verification_result=res_replay,
        )

    def execute_monogamy_scrambling_replay(
        self,
        verifier: VerifierBob,
        original_package: SignaturePackage,
        fresh_epr_pairs: List[DensityMatrix],
    ) -> AttackResult:
        """
        Adversary injects previously captured (b1, b2) tokens claiming a new nonce,
        attempting to apply them to newly distributed Bell pairs.
        Entanglement monogamy violation: Applying past Pauli corrections to fresh
        entangled qubits scrambles state into maximally mixed state, causing
        measured QBER >= 45%.
        """
        # Bob receives his half of fresh Bell pairs
        fresh_bob_qubits = [epr.partial_trace("A") for epr in fresh_epr_pairs]

        # Use new fresh nonce to test purely quantum physical monogamy detection
        scrambled_pkg = SignaturePackage(
            message=original_package.message,
            tokens=original_package.tokens,
            nonce=verifier.nonce_cache.generate_nonce(),
            timestamp=original_package.timestamp,
        )

        sprt = SPRTDetector()
        res = verifier.verify_signature(scrambled_pkg, fresh_bob_qubits, sprt_detector=sprt)

        detected = (not res.is_valid) or (res.qber >= 0.45)
        details = (
            f"Monogamy replay detected={detected}. QBER={res.qber:.2%} (expected >= 45%), "
            f"Mean Fidelity={res.mean_fidelity:.4f}"
        )

        return AttackResult(
            attack_type="REPLAY_MONOGAMY_VIOLATION",
            detected=detected,
            detection_mechanism="ENTANGLEMENT_CONSUMPTION_QBER",
            metric_value=res.qber,
            details=details,
            verification_result=res,
        )


class MITMInterception:
    """
    Simulates quantum channel eavesdropping:
    1. Intercept-Resend: Eavesdropper measures distributed qubit in computational
       or Hadamard basis, destroying entanglement. CHSH S <= 2.0 (classical limit).
    2. Beam-Splitting Tap: Eavesdropper extracts fraction of photons, degrading
       entanglement fidelity. CHSH drops S < 2.4.
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self.chsh_analyzer = CHSHAnalyzer()

    def intercept_resend(self, bell_pair: DensityMatrix) -> DensityMatrix:
        """
        Eve measures Bob's qubit in computational basis Z {|0>, |1>} and resends.
        State collapses to classical mixture:
          rho_sep = 1/2 |00><00| + 1/2 |11><11|
        Entanglement is completely destroyed.
        """
        P0 = PauliOperatorSet.P_0
        P1 = PauliOperatorSet.P_1
        I = PauliOperatorSet.I

        # Eve measures subsystem B
        P0_b = np.kron(I, P0)
        P1_b = np.kron(I, P1)

        mat = bell_pair.data
        collapsed_0 = P0_b @ mat @ P0_b
        collapsed_1 = P1_b @ mat @ P1_b

        rho_intercepted = collapsed_0 + collapsed_1
        return DensityMatrix(rho_intercepted)

    def beam_splitting_tap(
        self, bell_pair: DensityMatrix, tap_fraction: float = 0.35
    ) -> DensityMatrix:
        """
        Simulates beam splitting tap or partial entanglement degradation.
        Introduces severe depolarizing noise corresponding to tap ratio.
        """
        channel = QuantumChannel(depolarizing_prob=tap_fraction)
        return channel.transmit_qubit_in_bipartite(bell_pair, noisy_subsystem="B")

    def execute_mitm_attack(
        self, attack_mode: str = "intercept_resend"
    ) -> AttackResult:
        """
        Runs CHSH evaluation under quantum channel MITM.
        Decision rule: Abort channel if S <= 2.0 (classical limit) or S < 2.4.
        """
        clean_epr = EPRSource.create_bell_pair("Phi+")

        if attack_mode == "intercept_resend":
            compromised_epr = self.intercept_resend(clean_epr)
            chsh_res = self.chsh_analyzer.evaluate_density_matrix(compromised_epr)
            detected = not chsh_res.is_secure  # S <= 2.0 or S < 2.4
            details = (
                f"Intercept-Resend MITM detected={detected}. CHSH S={chsh_res.s_value:.4f} "
                f"(classical limit <= 2.0). Channel Status={chsh_res.status}."
            )
        elif attack_mode == "beam_splitting":
            compromised_epr = self.beam_splitting_tap(clean_epr, tap_fraction=0.35)
            chsh_res = self.chsh_analyzer.evaluate_density_matrix(compromised_epr)
            detected = not chsh_res.is_secure  # S < 2.4
            details = (
                f"Beam-splitting tap detected={detected}. CHSH S={chsh_res.s_value:.4f} "
                f"(degraded below 2.4). Channel Status={chsh_res.status}."
            )
        else:
            raise ValueError(f"Unknown attack_mode: {attack_mode}")

        return AttackResult(
            attack_type=f"MITM_{attack_mode.upper()}",
            detected=detected,
            detection_mechanism="BELL_CHSH_VIOLATION_ABORT",
            metric_value=chsh_res.s_value,
            details=details,
            chsh_result=chsh_res,
        )
