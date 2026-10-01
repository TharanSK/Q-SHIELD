"""
Sprint 1 Acceptance Tests: Quantum Foundations.

Acceptance Gates:
- State teleportation fidelity F > 0.999 in noiseless environment.
- Verified unitary Pauli transformations: U = (sigma_x^b2) * (sigma_z^b1).
- Density matrix state representation engine, purity, and partial traces.
- Depolarizing, phase-flip, and bit-flip noise channels.
"""

import pytest
import numpy as np

from qshield.core.quantum import (
    PauliOperatorSet,
    QuantumState,
    DensityMatrix,
    EPRSource,
    QuantumChannel,
    fidelity,
    state_fidelity,
)


def test_pauli_operators_algebra():
    """Verify algebraic properties of Pauli operators."""
    I, X, Y, Z = PauliOperatorSet.I, PauliOperatorSet.X, PauliOperatorSet.Y, PauliOperatorSet.Z

    # Unitary: U @ U^dagger = I
    for U in [I, X, Y, Z]:
        assert np.allclose(U @ U.conj().T, I)
        assert np.allclose(U @ U, I)

    # Involutory and anticommutation
    assert np.allclose(X @ Y, 1j * Z)
    assert np.allclose(Y @ Z, 1j * X)
    assert np.allclose(Z @ X, 1j * Y)


def test_mub_states_and_projectors():
    """Verify Mutually Unbiased Bases (MUBs): Computational Z, Hadamard X, Circular Y."""
    for basis in ["Z", "X", "Y"]:
        states = list(PauliOperatorSet.MUB_STATES[basis].values())
        psi0, psi1 = states[0], states[1]

        # Orthonormality within basis
        assert np.isclose(np.linalg.norm(psi0), 1.0)
        assert np.isclose(np.linalg.norm(psi1), 1.0)
        assert np.isclose(np.vdot(psi0, psi1), 0.0)

        # Projectors
        P0 = PauliOperatorSet.get_mub_projector(basis, "0")
        P1 = PauliOperatorSet.get_mub_projector(basis, "1")
        assert np.allclose(P0 @ P0, P0)
        assert np.allclose(P1 @ P1, P1)
        assert np.allclose(P0 + P1, PauliOperatorSet.I)

    # Conjugate basis mutual overlap: |<psi_i | phi_j>|^2 = 1/d = 0.50
    overlap_zx = abs(np.vdot(PauliOperatorSet.KET_0, PauliOperatorSet.KET_PLUS)) ** 2
    overlap_zy = abs(np.vdot(PauliOperatorSet.KET_0, PauliOperatorSet.KET_PLUS_I)) ** 2
    overlap_xy = abs(np.vdot(PauliOperatorSet.KET_PLUS, PauliOperatorSet.KET_PLUS_I)) ** 2
    assert np.isclose(overlap_zx, 0.50)
    assert np.isclose(overlap_zy, 0.50)
    assert np.isclose(overlap_xy, 0.50)


def test_density_matrix_purity_and_partial_trace():
    """Verify density matrix purity and partial trace operations."""
    bell = EPRSource.create_bell_pair("Phi+")
    assert np.isclose(bell.purity, 1.0)

    # Tracing out subsystem A leaves subsystem B in maximally mixed state I/2
    bob_reduced = bell.partial_trace("A")
    assert bob_reduced.dim == 2
    assert np.allclose(bob_reduced.data, np.eye(2, dtype=complex) / 2.0)
    assert np.isclose(bob_reduced.purity, 0.50)

    # Tracing out subsystem B leaves subsystem A in maximally mixed state
    alice_reduced = bell.partial_trace("B")
    assert np.allclose(alice_reduced.data, np.eye(2, dtype=complex) / 2.0)


def test_noiseless_teleportation_fidelity_gate():
    """
    SPRINT 1 ACCEPTANCE GATE:
    State teleportation fidelity F > 0.999 in noiseless environment across
    all MUB carrier states and all 4 Bell measurement outcomes.
    """
    test_carrier_states = [
        PauliOperatorSet.KET_0,
        PauliOperatorSet.KET_1,
        PauliOperatorSet.KET_PLUS,
        PauliOperatorSet.KET_MINUS,
        PauliOperatorSet.KET_PLUS_I,
        PauliOperatorSet.KET_MINUS_I,
        # Arbitrary superposition
        np.array([0.6, 0.8j], dtype=complex) / np.linalg.norm([0.6, 0.8j]),
    ]

    for psi in test_carrier_states:
        rho_c = np.outer(psi, psi.conj())
        rho_ab = EPRSource.create_bell_pair("Phi+").data
        rho_cab = np.kron(rho_c, rho_ab)

        for (b1, b2), P_ca in EPRSource.BSM_PROJECTORS.items():
            P_cab = np.kron(P_ca, PauliOperatorSet.I)
            prob = np.trace(P_cab @ rho_cab).real
            assert np.isclose(prob, 0.25), f"Bell outcome ({b1}, {b2}) probability must be 0.25"

            # Post-measurement state
            collapsed_cab = (P_cab @ rho_cab @ P_cab) / prob
            # Trace out CA
            reshaped = collapsed_cab.reshape(2, 2, 2, 2, 2, 2)
            rho_b = np.einsum("ijkijl->kl", reshaped)

            # Pauli recovery unitary: U = (sigma_x^b2) * (sigma_z^b1)
            U = PauliOperatorSet.get_recovery_unitary(b1, b2)
            rho_out = U @ rho_b @ U.conj().T

            # Projective fidelity
            f = state_fidelity(psi, rho_out)
            assert f > 0.999, f"Teleportation fidelity {f} failed Acceptance Gate (> 0.999) for outcome ({b1}, {b2})"


def test_quantum_channel_depolarizing_and_noise_models():
    """Verify physical quantum channel noise behavior."""
    pure_0 = DensityMatrix(np.outer(PauliOperatorSet.KET_0, PauliOperatorSet.KET_0.conj()))

    # Noiseless channel
    ch_clean = QuantumChannel(depolarizing_prob=0.0)
    assert np.allclose(ch_clean.apply_single_qubit_noise(pure_0).data, pure_0.data)

    # 100% depolarizing channel: output must be maximally mixed state I/2
    ch_max = QuantumChannel(depolarizing_prob=1.0)
    noisy_max = ch_max.apply_single_qubit_noise(pure_0)
    assert np.allclose(noisy_max.data, np.eye(2, dtype=complex) / 2.0, atol=1e-5)
    assert np.isclose(noisy_max.purity, 0.50)

    # Partial noise monotonically reduces purity
    ch_10 = QuantumChannel(depolarizing_prob=0.10)
    noisy_10 = ch_10.apply_single_qubit_noise(pure_0)
    assert noisy_10.purity < pure_0.purity
    assert noisy_10.purity > 0.50
