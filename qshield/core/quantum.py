"""
Quantum core module for Q-SHIELD.

Provides high-performance density matrix state representation, Pauli operator algebra,
Mutually Unbiased Bases (MUBs), Bell state EPR pair generation, quantum channel noise models,
and projective fidelity metrics.
"""

from __future__ import annotations
import numpy as np
from typing import Tuple, Dict, Optional, Union, List


class PauliOperatorSet:
    """Pauli unitary operators and Mutually Unbiased Bases (MUBs)."""

    # Basic Pauli 2x2 matrices
    I = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=complex)
    X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
    Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=complex)
    Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)

    # Basis pure state vectors
    # Computational Z basis
    KET_0 = np.array([1.0, 0.0], dtype=complex)
    KET_1 = np.array([0.0, 1.0], dtype=complex)

    # Hadamard X basis
    KET_PLUS = np.array([1.0, 1.0], dtype=complex) / np.sqrt(2.0)
    KET_MINUS = np.array([1.0, -1.0], dtype=complex) / np.sqrt(2.0)

    # Circular Y basis
    KET_PLUS_I = np.array([1.0, 1.0j], dtype=complex) / np.sqrt(2.0)
    KET_MINUS_I = np.array([1.0, -1.0j], dtype=complex) / np.sqrt(2.0)

    # Projectors for each basis state P = |psi><psi|
    P_0 = np.outer(KET_0, KET_0.conj())
    P_1 = np.outer(KET_1, KET_1.conj())
    P_PLUS = np.outer(KET_PLUS, KET_PLUS.conj())
    P_MINUS = np.outer(KET_MINUS, KET_MINUS.conj())
    P_PLUS_I = np.outer(KET_PLUS_I, KET_PLUS_I.conj())
    P_MINUS_I = np.outer(KET_MINUS_I, KET_MINUS_I.conj())

    # Map of basis name to eigenstates and projectors
    MUB_STATES: Dict[str, Dict[str, np.ndarray]] = {
        "Z": {"0": KET_0, "1": KET_1},
        "X": {"+": KET_PLUS, "-": KET_MINUS},
        "Y": {"+i": KET_PLUS_I, "-i": KET_MINUS_I},
    }

    MUB_PROJECTORS: Dict[str, Dict[str, np.ndarray]] = {
        "Z": {"0": P_0, "1": P_1},
        "X": {"+": P_PLUS, "-": P_MINUS},
        "Y": {"+i": P_PLUS_I, "-i": P_MINUS_I},
    }

    @staticmethod
    def get_recovery_unitary(b1: int, b2: int) -> np.ndarray:
        """
        Calculates verifier's Pauli recovery unitary:
        U = (sigma_x^b2) * (sigma_z^b1)
        where (b1, b2) in {00, 01, 10, 11}.
        """
        # (sigma_x)^b2: if b2==1 then X else I
        # (sigma_z)^b1: if b1==1 then Z else I
        term_x = PauliOperatorSet.X if b2 == 1 else PauliOperatorSet.I
        term_z = PauliOperatorSet.Z if b1 == 1 else PauliOperatorSet.I
        return term_x @ term_z

    @staticmethod
    def get_mub_state(basis: str, bit: Union[int, str]) -> np.ndarray:
        """Fetch pure state vector for a given basis and bit value."""
        if basis == "Z":
            key = "0" if str(bit) in ("0", "KET_0") else "1"
        elif basis == "X":
            key = "+" if str(bit) in ("0", "+") else "-"
        elif basis == "Y":
            key = "+i" if str(bit) in ("0", "+i") else "-i"
        else:
            raise ValueError(f"Invalid MUB basis: {basis}. Expected 'Z', 'X', or 'Y'.")
        return PauliOperatorSet.MUB_STATES[basis][key]

    @staticmethod
    def get_mub_projector(basis: str, bit: Union[int, str]) -> np.ndarray:
        """Fetch projector for a given basis and bit value."""
        if basis == "Z":
            key = "0" if str(bit) in ("0", "KET_0") else "1"
        elif basis == "X":
            key = "+" if str(bit) in ("0", "+") else "-"
        elif basis == "Y":
            key = "+i" if str(bit) in ("0", "+i") else "-i"
        else:
            raise ValueError(f"Invalid MUB basis: {basis}. Expected 'Z', 'X', or 'Y'.")
        return PauliOperatorSet.MUB_PROJECTORS[basis][key]


class QuantumState:
    """Represents a pure quantum state vector."""

    def __init__(self, vector: np.ndarray):
        vec = np.asarray(vector, dtype=complex).reshape(-1)
        norm = np.linalg.norm(vec)
        if norm < 1e-12:
            raise ValueError("State vector norm cannot be zero.")
        self.vector = vec / norm
        self.dim = len(self.vector)

    def to_density_matrix(self) -> DensityMatrix:
        rho = np.outer(self.vector, self.vector.conj())
        return DensityMatrix(rho)

    def __repr__(self) -> str:
        return f"QuantumState(dim={self.dim}, vector={np.round(self.vector, 3)})"


class DensityMatrix:
    """Represents a quantum density matrix rho."""

    def __init__(self, matrix: np.ndarray, check_valid: bool = False):
        mat = np.asarray(matrix, dtype=complex)
        if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
            raise ValueError("Density matrix must be square.")
        # Ensure Hermiticity
        mat = (mat + mat.conj().T) / 2.0
        # Normalize trace
        tr = np.trace(mat).real
        if tr > 1e-12:
            mat = mat / tr
        self.data = mat
        self.dim = mat.shape[0]

        if check_valid:
            eigvals = np.linalg.eigvalsh(self.data)
            if np.any(eigvals < -1e-7):
                raise ValueError(f"Density matrix has negative eigenvalues: {eigvals}")

    @property
    def purity(self) -> float:
        """Purity gamma = Tr(rho^2). 1.0 for pure states, 1/d for maximally mixed."""
        return float(np.trace(self.data @ self.data).real)

    def partial_trace(self, system: str, dims: Optional[List[int]] = None) -> DensityMatrix:
        """
        Compute partial trace over subsystems.
        Supports 2-qubit ('A' or 'B') and 3-qubit ('CA', 'C', 'A', 'B') systems.
        """
        if dims is None:
            # Determine qubit count based on dim
            if self.dim == 4:
                dims = [2, 2]
            elif self.dim == 8:
                dims = [2, 2, 2]
            else:
                raise ValueError(f"Explicit dims required for dimension {self.dim}")

        if len(dims) == 2:
            reshaped = self.data.reshape(dims[0], dims[1], dims[0], dims[1])
            if system.upper() == "A":
                # Trace out A (subsystem 0) -> leaves B (subsystem 1)
                # indices: i (A), j (B), i (A'), l (B') -> j, l
                res = np.einsum("ijil->jl", reshaped)
            elif system.upper() == "B":
                # Trace out B (subsystem 1) -> leaves A (subsystem 0)
                # indices: i (A), j (B), k (A'), j (B') -> i, k
                res = np.einsum("ijik->ik", reshaped)
            else:
                raise ValueError(f"Unknown subsystem {system} for 2-qubit system.")
            return DensityMatrix(res)

        elif len(dims) == 3:
            reshaped = self.data.reshape(dims[0], dims[1], dims[2], dims[0], dims[1], dims[2])
            if system.upper() == "CA":
                # Trace out C (0) and A (1) -> leaves B (2)
                # indices: i (C), j (A), k (B), i (C'), j (A'), l (B') -> k, l
                res = np.einsum("ijkijl->kl", reshaped)
            elif system.upper() == "C":
                # Trace out C (0) -> leaves AB (1, 2)
                # indices: i (C), j (A), k (B), i (C'), l (A'), m (B') -> (j*2+k), (l*2+m)
                res = np.einsum("ijkilm->jklm", reshaped).reshape(4, 4)
            elif system.upper() == "B":
                # Trace out B (2) -> leaves CA (0, 1)
                # indices: i (C), j (A), k (B), l (C'), m (A'), k (B') -> (i*2+j), (l*2+m)
                res = np.einsum("ijkimk->ijim", reshaped).reshape(4, 4)
            else:
                raise NotImplementedError(f"Partial trace for {system} on 3-qubit system.")
            return DensityMatrix(res)

        raise ValueError(f"Unsupported system configuration: dims={dims}, system={system}")

    def expectation_value(self, operator: np.ndarray) -> float:
        """Compute expectation value <O> = Tr(O * rho)."""
        return float(np.trace(operator @ self.data).real)

    def project(self, projector: np.ndarray) -> Tuple[float, Optional[DensityMatrix]]:
        """
        Project state using P.
        Returns:
            probability: Tr(P * rho)
            collapsed_rho: P * rho * P / prob (or None if prob == 0)
        """
        prob = float(np.trace(projector @ self.data).real)
        if prob <= 1e-12:
            return 0.0, None
        collapsed = (projector @ self.data @ projector) / prob
        return prob, DensityMatrix(collapsed)

    def __repr__(self) -> str:
        return f"DensityMatrix(dim={self.dim}, purity={self.purity:.4f})"


def fidelity(rho: Union[DensityMatrix, np.ndarray], sigma: Union[DensityMatrix, np.ndarray]) -> float:
    """
    Computes quantum fidelity between two states.
    For pure reference state |psi><psi|, F(rho, |psi>) = <psi|rho|psi>.
    For general states, returns Uhlmann fidelity: (Tr sqrt(sqrt(rho) * sigma * sqrt(rho)))^2.
    """
    r_mat = rho.data if isinstance(rho, DensityMatrix) else np.asarray(rho, dtype=complex)
    s_mat = sigma.data if isinstance(sigma, DensityMatrix) else np.asarray(sigma, dtype=complex)

    # Check if either state is essentially pure
    r_pure = np.isclose(np.trace(r_mat @ r_mat).real, 1.0, atol=1e-5)
    s_pure = np.isclose(np.trace(s_mat @ s_mat).real, 1.0, atol=1e-5)

    if r_pure or s_pure:
        # F = Tr(rho * sigma)
        val = np.trace(r_mat @ s_mat).real
        return float(np.clip(val, 0.0, 1.0))

    # General Uhlmann fidelity: (Tr(sqrt(sqrt(r) * s * sqrt(r))))^2
    eigvals_r, eigvecs_r = np.linalg.eigh(r_mat)
    eigvals_r = np.maximum(eigvals_r, 0.0)
    sqrt_r = eigvecs_r @ np.diag(np.sqrt(eigvals_r)) @ eigvecs_r.conj().T

    inner = sqrt_r @ s_mat @ sqrt_r
    eigvals_inner = np.linalg.eigvalsh(inner)
    eigvals_inner = np.maximum(eigvals_inner, 0.0)
    fid = float(np.sum(np.sqrt(eigvals_inner)) ** 2)
    return float(np.clip(fid, 0.0, 1.0))


def state_fidelity(psi: Union[QuantumState, np.ndarray], rho: Union[DensityMatrix, np.ndarray]) -> float:
    """
    Projective fidelity F = <psi|rho|psi> = Tr(P_psi * rho).
    """
    psi_vec = psi.vector if isinstance(psi, QuantumState) else np.asarray(psi, dtype=complex).reshape(-1)
    rho_mat = rho.data if isinstance(rho, DensityMatrix) else np.asarray(rho, dtype=complex)
    f = np.vdot(psi_vec, rho_mat @ psi_vec).real
    return float(np.clip(f, 0.0, 1.0))


class EPRSource:
    """
    Simulates maximally entangled 2-qubit Bell pairs.
    Default: |Phi+> = 1/sqrt(2) (|00> + |11>).
    """

    # 4 Bell states
    PHI_PLUS = np.array([1.0, 0.0, 0.0, 1.0], dtype=complex) / np.sqrt(2.0)
    PHI_MINUS = np.array([1.0, 0.0, 0.0, -1.0], dtype=complex) / np.sqrt(2.0)
    PSI_PLUS = np.array([0.0, 1.0, 1.0, 0.0], dtype=complex) / np.sqrt(2.0)
    PSI_MINUS = np.array([0.0, 1.0, -1.0, 0.0], dtype=complex) / np.sqrt(2.0)

    BELL_VECTORS = {
        "Phi+": PHI_PLUS,
        "Phi-": PHI_MINUS,
        "Psi+": PSI_PLUS,
        "Psi-": PSI_MINUS,
    }

    # BSM Outcome mapping to Bell state projectors
    # (b1, b2):
    # 00 -> Phi+
    # 10 -> Phi-
    # 01 -> Psi+
    # 11 -> Psi-
    BSM_PROJECTORS = {
        (0, 0): np.outer(PHI_PLUS, PHI_PLUS.conj()),
        (1, 0): np.outer(PHI_MINUS, PHI_MINUS.conj()),
        (0, 1): np.outer(PSI_PLUS, PSI_PLUS.conj()),
        (1, 1): np.outer(PSI_MINUS, PSI_MINUS.conj()),
    }

    @classmethod
    def create_bell_pair(cls, bell_type: str = "Phi+") -> DensityMatrix:
        """Generate a single 2-qubit Bell pair density matrix."""
        vec = cls.BELL_VECTORS.get(bell_type, cls.PHI_PLUS)
        rho = np.outer(vec, vec.conj())
        return DensityMatrix(rho)

    @classmethod
    def create_batch(cls, count: int, bell_type: str = "Phi+") -> List[DensityMatrix]:
        """Generate a list of count independent Bell pairs."""
        return [cls.create_bell_pair(bell_type) for _ in range(count)]


class QuantumChannel:
    """
    Simulates physical quantum transmission channels with depolarizing,
    phase-flip, and bit-flip noise models.
    """

    def __init__(
        self,
        depolarizing_prob: float = 0.0,
        phase_flip_prob: float = 0.0,
        bit_flip_prob: float = 0.0,
        rng: Optional[np.random.Generator] = None,
    ):
        self.depolarizing_prob = max(0.0, min(1.0, depolarizing_prob))
        self.phase_flip_prob = max(0.0, min(1.0, phase_flip_prob))
        self.bit_flip_prob = max(0.0, min(1.0, bit_flip_prob))
        self.rng = rng or np.random.default_rng()

    def apply_single_qubit_noise(self, rho: DensityMatrix) -> DensityMatrix:
        """
        Applies configured noise to a 1-qubit density matrix.
        Depolarizing channel:
          E(rho) = (1 - p)*rho + p/3 * (X*rho*X + Y*rho*Y + Z*rho*Z)
        Phase-flip channel:
          E(rho) = (1 - p_z)*rho + p_z * (Z*rho*Z)
        Bit-flip channel:
          E(rho) = (1 - p_x)*rho + p_x * (X*rho*X)
        """
        mat = rho.data.copy()
        X, Y, Z = PauliOperatorSet.X, PauliOperatorSet.Y, PauliOperatorSet.Z

        # Bit-flip
        if self.bit_flip_prob > 0.0:
            p_x = self.bit_flip_prob
            mat = (1.0 - p_x) * mat + p_x * (X @ mat @ X)

        # Phase-flip
        if self.phase_flip_prob > 0.0:
            p_z = self.phase_flip_prob
            mat = (1.0 - p_z) * mat + p_z * (Z @ mat @ Z)

        # Depolarizing channel: E(rho) = (1 - p)*rho + p * (I / 2)
        if self.depolarizing_prob > 0.0:
            p = self.depolarizing_prob
            mat = (1.0 - p) * mat + p * (PauliOperatorSet.I / 2.0)

        return DensityMatrix(mat)

    def transmit_qubit_in_bipartite(
        self, rho_ab: DensityMatrix, noisy_subsystem: str = "B"
    ) -> DensityMatrix:
        """
        Applies noise to one subsystem (e.g. Bob's qubit B) of a 2-qubit state rho_AB.
        Kraus representation applied to subsystem B:
        rho' = sum_k (I_A (x) K_k) rho_AB (I_A (x) K_k^dagger)
        """
        mat = rho_ab.data.copy()
        I = PauliOperatorSet.I
        X, Y, Z = PauliOperatorSet.X, PauliOperatorSet.Y, PauliOperatorSet.Z

        kraus_ops = []

        # Canonical Depolarizing channel Kraus operators:
        # E(rho) = (1 - p)*rho + p*(I/2) = (1 - 3p/4)*rho + (p/4)*(X*rho*X + Y*rho*Y + Z*rho*Z)
        p = self.depolarizing_prob
        if p > 0.0:
            k0 = np.sqrt(1.0 - 0.75 * p) * I
            kx = np.sqrt(0.25 * p) * X
            ky = np.sqrt(0.25 * p) * Y
            kz = np.sqrt(0.25 * p) * Z
            kraus_ops.append([k0, kx, ky, kz])

        # Phase flip
        pz = self.phase_flip_prob
        if pz > 0.0:
            k0 = np.sqrt(1.0 - pz) * I
            kz = np.sqrt(pz) * Z
            kraus_ops.append([k0, kz])

        # Bit flip
        px = self.bit_flip_prob
        if px > 0.0:
            k0 = np.sqrt(1.0 - px) * I
            kx = np.sqrt(px) * X
            kraus_ops.append([k0, kx])

        if not kraus_ops:
            return DensityMatrix(mat)

        # Apply sequential noise channels to subsystem
        for op_list in kraus_ops:
            accum = np.zeros_like(mat)
            for K in op_list:
                if noisy_subsystem.upper() == "B":
                    full_K = np.kron(I, K)
                else:
                    full_K = np.kron(K, I)
                accum += full_K @ mat @ full_K.conj().T
            mat = accum

        return DensityMatrix(mat)
