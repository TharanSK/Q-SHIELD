"""
Quantum Digital Signature (QDS) protocol implementation using quantum teleportation.

Features:
- SignerAlice: Encodes message into carrier states across MUBs (Z, X, Y) and performs joint BSM.
- VerifierBob: Applies Pauli recovery unitary, performs conjugate projective checks, and enforces nonce caching.
- EpochNonceCache: Monotonic epoch challenge nonce validation for replay protection.
- TeleportationPipeline: End-to-end distributed execution harness with quantum channel noise.
"""

from __future__ import annotations
import secrets
import time
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
import numpy as np

from qshield.core.quantum import (
    PauliOperatorSet,
    QuantumState,
    DensityMatrix,
    EPRSource,
    QuantumChannel,
    state_fidelity,
)


@dataclass
class SignatureToken:
    """A single teleportation classical payload token."""
    b1: int
    b2: int
    basis: str  # 'Z', 'X', or 'Y'
    bit_value: int  # 0 or 1
    is_decoy: bool = False


@dataclass
class SignaturePackage:
    """The classical package transmitted from Signer to Verifier."""
    message: str
    tokens: List[SignatureToken]
    nonce: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of signature verification and threat analysis."""
    is_valid: bool
    qber: float
    mean_fidelity: float
    total_qubits: int
    test_qubits: int
    sprt_log_likelihood: float
    decision: str  # 'ACCEPTED', 'REJECTED_FORGERY', 'REJECTED_REPLAY', 'REJECTED_NOISE'
    rejection_reason: Optional[str] = None
    fidelities: List[float] = field(default_factory=list)


class EpochNonceCache:
    """
    Epoch challenge nonce cache to detect and reject token replay attacks.
    Maintains a record of consumed nonces with time-to-live (TTL).
    """

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl_seconds = ttl_seconds
        self.consumed_nonces: Dict[str, float] = {}

    def generate_nonce(self) -> str:
        """Generate a cryptographically secure 256-bit hexadecimal nonce."""
        nonce = secrets.token_hex(32)
        return nonce

    def is_valid_and_consume(self, nonce: str, current_time: Optional[float] = None) -> bool:
        """
        Validates that a nonce is fresh and unconsumed, then records it.
        Returns False if the nonce has already been consumed or has expired.
        """
        now = current_time if current_time is not None else time.time()
        self._cleanup(now)

        if not nonce or nonce in self.consumed_nonces:
            return False

        self.consumed_nonces[nonce] = now
        return True

    def _cleanup(self, now: float) -> None:
        """Evicts expired nonces older than TTL."""
        expired = [n for n, ts in self.consumed_nonces.items() if (now - ts) > self.ttl_seconds]
        for n in expired:
            del self.consumed_nonces[n]


class SignerAlice:
    """
    Signer entity:
    - Generates carrier states chosen randomly across MUBs (Z, X, Y).
    - Performs joint Bell-State Measurement (BSM) on carrier state and entangled qubit A.
    - Yields deterministic classical 2-bit teleportation payload (b1, b2).
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def generate_carrier_states(
        self, length: int, decoy_ratio: float = 0.5
    ) -> List[Tuple[np.ndarray, str, int, bool]]:
        """
        Generates carrier states |psi> = alpha|0> + beta|1> chosen across MUBs:
        Computational Z, Hadamard X, Circular Y.
        Returns list of (state_vector, basis, bit_value, is_decoy).
        """
        bases = ["Z", "X", "Y"]
        carrier_states = []
        for _ in range(length):
            basis = str(self.rng.choice(bases))
            bit_val = int(self.rng.integers(0, 2))
            is_decoy = bool(self.rng.random() < decoy_ratio)
            vec = PauliOperatorSet.get_mub_state(basis, bit_val)
            carrier_states.append((vec, basis, bit_val, is_decoy))
        return carrier_states

    def sign_message(
        self,
        message: str,
        epr_pairs: List[DensityMatrix],
        decoy_ratio: float = 0.5,
        nonce: Optional[str] = None,
    ) -> Tuple[SignaturePackage, List[DensityMatrix]]:
        """
        Performs BSM on Alice's carrier qubits and entangled qubits A.
        Returns (signature_package, bob_qubit_states).
        """
        n_qubits = len(epr_pairs)
        carriers = self.generate_carrier_states(n_qubits, decoy_ratio=decoy_ratio)
        tokens: List[SignatureToken] = []
        bob_states: List[DensityMatrix] = []

        bsm_keys = list(EPRSource.BSM_PROJECTORS.keys())

        for i, (psi_c, basis, bit_val, is_decoy) in enumerate(carriers):
            rho_c = np.outer(psi_c, psi_c.conj())
            rho_ab = epr_pairs[i].data

            # 3-qubit joint density matrix C (carrier), A (Alice entangled), B (Bob entangled)
            rho_cab = np.kron(rho_c, rho_ab)

            # Perform joint BSM on qubits C and A
            # Calculate probabilities for all 4 Bell outcomes
            probs = []
            post_states = []
            for outcome in bsm_keys:
                P_ca = EPRSource.BSM_PROJECTORS[outcome]
                P_cab = np.kron(P_ca, PauliOperatorSet.I)
                prob = float(np.trace(P_cab @ rho_cab).real)
                probs.append(max(0.0, prob))
                post_states.append(P_cab @ rho_cab @ P_cab)

            total_prob = sum(probs)
            if total_prob > 1e-12:
                norm_probs = [p / total_prob for p in probs]
            else:
                norm_probs = [0.25] * 4

            # Sample outcome deterministically from quantum state projection
            chosen_idx = int(self.rng.choice(len(bsm_keys), p=norm_probs))
            b1, b2 = bsm_keys[chosen_idx]

            # Collapsed joint state
            collapsed_cab = post_states[chosen_idx] / probs[chosen_idx]
            # Trace out CA to obtain Bob's qubit B
            reshaped = collapsed_cab.reshape(2, 2, 2, 2, 2, 2)
            rho_b = np.einsum("ijkijl->kl", reshaped)

            bob_states.append(DensityMatrix(rho_b))
            tokens.append(
                SignatureToken(
                    b1=b1,
                    b2=b2,
                    basis=basis,
                    bit_value=bit_val,
                    is_decoy=is_decoy,
                )
            )

        pkg_nonce = nonce if nonce is not None else secrets.token_hex(32)
        package = SignaturePackage(
            message=message,
            tokens=tokens,
            nonce=pkg_nonce,
        )
        return package, bob_states


class VerifierBob:
    """
    Verifier entity:
    - Validates epoch challenge nonce to prevent replay attacks.
    - Applies Pauli recovery unitary U = (sigma_x^b2) * (sigma_z^b1).
    - Measures fidelity and projective checks across MUB bases.
    - Evaluates Quantum Bit Error Rate (QBER) and decides authenticity.
    """

    def __init__(
        self,
        nonce_cache: Optional[EpochNonceCache] = None,
        fidelity_threshold: float = 0.85,
    ):
        self.nonce_cache = nonce_cache or EpochNonceCache()
        self.fidelity_threshold = fidelity_threshold

    def verify_signature(
        self,
        package: SignaturePackage,
        bob_qubits: List[DensityMatrix],
        sprt_detector: Optional[any] = None,
    ) -> VerificationResult:
        """
        Verifies received signature package against Bob's received quantum states.
        Enforces:
        1. Epoch challenge nonce validation.
        2. Pauli unitary reconstruction: U = (sigma_x^b2) * (sigma_z^b1).
        3. Projective measurement checks Tr(P_psi * rho_out).
        4. Sequential Probability Ratio Test (SPRT) evaluation.
        """
        # Step 1: Replay protection via Nonce Cache
        if not self.nonce_cache.is_valid_and_consume(package.nonce, package.timestamp):
            return VerificationResult(
                is_valid=False,
                qber=1.0,
                mean_fidelity=0.0,
                total_qubits=len(package.tokens),
                test_qubits=0,
                sprt_log_likelihood=999.0,
                decision="REJECTED_REPLAY",
                rejection_reason="REPLAY_ATTACK: Reused or expired epoch challenge nonce.",
            )

        fidelities = []
        error_sequence = []
        n_tokens = len(package.tokens)

        # Step 2 & 3: Pauli Unitary Reconstruction and Projective Checks
        for token, rho_b in zip(package.tokens, bob_qubits):
            # Recovery unitary: U = (sigma_x^b2) * (sigma_z^b1)
            U = PauliOperatorSet.get_recovery_unitary(token.b1, token.b2)
            rho_out = U @ rho_b.data @ U.conj().T

            # Expected target state |psi> and projector P_psi
            target_vec = PauliOperatorSet.get_mub_state(token.basis, token.bit_value)
            fid = state_fidelity(target_vec, rho_out)
            fidelities.append(fid)

            # Decoy/test check: projective state error if projective fidelity is below threshold
            # Under physical channel noise < 5%, legitimate fidelity remains > 0.85.
            # Under forgery or impersonation, fidelity drops to <= 0.50.
            is_error = 1 if fid < self.fidelity_threshold else 0
            error_sequence.append(is_error)

        qber = float(np.mean(error_sequence)) if error_sequence else 0.0
        mean_fid = float(np.mean(fidelities)) if fidelities else 0.0

        # Step 4: Threat decision via SPRT or threshold
        sprt_decision = "ACCEPTED"
        llr = 0.0

        if sprt_detector is not None:
            sprt_decision, llr = sprt_detector.evaluate_sequence(error_sequence)
            if sprt_decision == "REJECT_H1":
                return VerificationResult(
                    is_valid=False,
                    qber=qber,
                    mean_fidelity=mean_fid,
                    total_qubits=n_tokens,
                    test_qubits=len(error_sequence),
                    sprt_log_likelihood=llr,
                    decision="REJECTED_FORGERY",
                    rejection_reason=f"SPRT_FORGERY_DETECTED: Log-likelihood ratio {llr:.2f} exceeded threshold.",
                    fidelities=fidelities,
                )

        # Fallback deterministic check: QBER <= nominal error budget (e.g. 15%)
        # Forgery produces e >= 25%, Replay on fresh pairs produces e >= 45%
        is_valid = (qber < 0.15) and (mean_fid >= self.fidelity_threshold)
        decision = "ACCEPTED" if is_valid else "REJECTED_FORGERY"
        reason = None if is_valid else f"HIGH_QBER: Measured QBER {qber:.2%} exceeds threshold."

        return VerificationResult(
            is_valid=is_valid,
            qber=qber,
            mean_fidelity=mean_fid,
            total_qubits=n_tokens,
            test_qubits=len(error_sequence),
            sprt_log_likelihood=llr,
            decision=decision,
            rejection_reason=reason,
            fidelities=fidelities,
        )


class TeleportationPipeline:
    """
    End-to-end pipeline simulating state distribution, channel noise,
    signing, and verification.
    """

    def __init__(
        self,
        channel: Optional[QuantumChannel] = None,
        nonce_cache: Optional[EpochNonceCache] = None,
        seed: Optional[int] = None,
    ):
        self.channel = channel or QuantumChannel()
        self.alice = SignerAlice(seed=seed)
        self.bob = VerifierBob(nonce_cache=nonce_cache)

    def execute_protocol(
        self,
        message: str,
        n_qubits: int = 256,
        decoy_ratio: float = 0.5,
        sprt_detector: Optional[any] = None,
    ) -> Tuple[SignaturePackage, VerificationResult]:
        """
        Executes complete protocol:
        1. EPR generation
        2. Alice signing
        3. Bob qubit transmission through quantum channel
        4. Bob verification
        """
        # Step 1: Distributed Bell pairs
        bell_pairs = EPRSource.create_batch(n_qubits, "Phi+")

        # Step 2: Alice generates signature and extracts Bob's qubits
        package, raw_bob_qubits = self.alice.sign_message(
            message=message,
            epr_pairs=bell_pairs,
            decoy_ratio=decoy_ratio,
        )

        # Step 3: Transmit Bob's qubits through quantum channel (depolarizing/phase noise)
        noisy_bob_qubits = [
            self.channel.apply_single_qubit_noise(q) for q in raw_bob_qubits
        ]

        # Step 4: Bob verification
        result = self.bob.verify_signature(
            package=package,
            bob_qubits=noisy_bob_qubits,
            sprt_detector=sprt_detector,
        )

        return package, result
