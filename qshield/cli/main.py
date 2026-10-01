"""
Command-line interface (CLI) for Project Q-SHIELD.

Provides commands:
  qshield verify  - Teleportation QDS signing and verification
  qshield attack  - Threat injection simulation (forgery, replay, MITM)
  qshield chsh    - Bell-CHSH channel violation and eavesdropping test
  qshield bench   - Full security and performance benchmark suite
"""

from __future__ import annotations
import argparse
import sys
import time

from qshield.core.quantum import QuantumChannel, EPRSource
from qshield.protocol.qds import TeleportationPipeline, VerifierBob
from qshield.engine.stats import SPRTDetector, CHSHAnalyzer
from qshield.attacks.sim import ForgerySimulator, ReplayInjector, MITMInterception
from qshield.bench.eval import SecurityEvaluator, InformationTheoreticBound


def cmd_verify(args: argparse.Namespace) -> int:
    """Run signature verification over quantum channel."""
    print("=" * 60)
    print("  Q-SHIELD: TELEPORTATION-BASED QUANTUM SIGNING PIPELINE")
    print("=" * 60)
    print(f" Message        : '{args.message}'")
    print(f" Sample Qubits  : {args.samples}")
    print(f" Channel Noise  : {args.noise:.1%} (depolarizing)")

    channel = QuantumChannel(depolarizing_prob=args.noise)
    pipeline = TeleportationPipeline(channel=channel)
    sprt = SPRTDetector(p0=max(0.02, args.noise + 0.01), p1=0.25)

    t0 = time.perf_counter()
    pkg, res = pipeline.execute_protocol(
        message=args.message,
        n_qubits=args.samples,
        sprt_detector=sprt,
    )
    elapsed = (time.perf_counter() - t0) * 1000

    print("-" * 60)
    print(f" Protocol Status : {res.decision}")
    print(f" Authenticated   : {'[YES] VALID SIGNATURE' if res.is_valid else '[NO] SIGNATURE REJECTED'}")
    print(f" Measured QBER   : {res.qber:.2%}")
    print(f" Mean Fidelity   : {res.mean_fidelity:.4f}")
    print(f" SPRT LLR        : {res.sprt_log_likelihood:.2f}")
    print(f" Nonce           : {pkg.nonce[:16]}...")
    print(f" Total Elapsed   : {elapsed:.2f} ms")
    if res.rejection_reason:
        print(f" Alert Reason    : {res.rejection_reason}")
    print("=" * 60)
    return 0 if res.is_valid else 1


def cmd_attack(args: argparse.Namespace) -> int:
    """Run simulated cyber threat and display detection mechanics."""
    print("=" * 60)
    print("  Q-SHIELD: NON-ML QUANTUM THREAT DETECTION HARNESS")
    print("=" * 60)
    print(f" Threat Scenario: {args.type.upper()}")
    print(f" Sample Qubits  : {args.samples}")

    pipe = TeleportationPipeline()

    if args.type == "forgery":
        forger = ForgerySimulator()
        res = forger.execute_forgery_attack(pipe, n_qubits=args.samples)
    elif args.type == "impersonation":
        forger = ForgerySimulator()
        res = forger.execute_impersonation_attack(pipe.bob, n_qubits=args.samples)
    elif args.type == "replay":
        replay = ReplayInjector()
        res = replay.execute_nonce_replay(pipe, n_qubits=args.samples)
    elif args.type == "mitm":
        mitm = MITMInterception()
        res = mitm.execute_mitm_attack("intercept_resend")
    else:
        print(f"Unknown attack type: {args.type}")
        return 1

    print("-" * 60)
    print(f" Attack Intercepted : {'[SECURED] THREAT NEUTRALIZED' if res.detected else '[BREACH] ATTACK EVADED'}")
    print(f" Detection Engine   : {res.detection_mechanism}")
    print(f" Physical Metric    : {res.metric_value:.4f}")
    print(f" Forensic Details   : {res.details}")
    print("=" * 60)
    return 0 if res.detected else 1


def cmd_chsh(args: argparse.Namespace) -> int:
    """Run Bell-CHSH inequality evaluation for channel monitoring."""
    print("=" * 60)
    print("  Q-SHIELD: BELL-CHSH QUANTUM CHANNEL INTEGRITY")
    print("=" * 60)
    print(f" Channel Noise : {args.noise:.1%} depolarizing")

    analyzer = CHSHAnalyzer()
    channel = QuantumChannel(depolarizing_prob=args.noise)
    res = analyzer.evaluate_channel(channel)

    print("-" * 60)
    print(f" CHSH Parameter S : {res.s_value:.4f}")
    print(f" Classical Limit  : S <= 2.0000")
    print(f" Tsirelson Bound  : 2*sqrt(2) = 2.8284")
    print(f" Bell Violation   : {'YES (Quantum Correlated)' if res.is_violated else 'NO (Classical / MITM Eavesdropped)'}")
    print(f" Channel Status   : {res.status}")
    print(f" Action Required  : {'PROCEED WITH SIGNING' if res.is_secure else 'ABORT QUANTUM CHANNEL'}")
    print("=" * 60)
    return 0 if res.is_secure else 1


def cmd_bench(args: argparse.Namespace) -> int:
    """Run comprehensive performance and security benchmark."""
    evaluator = SecurityEvaluator()
    print(f"Executing Q-SHIELD benchmark ({args.trials} attack trials, {args.samples} verification qubits)...")
    report = evaluator.run_full_benchmark(
        n_attack_trials=args.trials,
        n_genuine_trials=args.trials,
        benchmark_qubits=args.samples,
    )
    report.print_summary()
    return 0 if report.passed_all_gates else 1


def main(argv: list[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="qshield",
        description="Project Q-SHIELD: Quantum-Inspired Cyber Threat Detection Framework",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # verify
    p_verify = subparsers.add_parser("verify", help="Execute teleportation-based QDS verification")
    p_verify.add_argument("--message", type=str, default="FINANCIAL_PAYLOAD_HASH_0x9A4F", help="Message to sign")
    p_verify.add_argument("--samples", type=int, default=256, help="Number of qubit carrier states")
    p_verify.add_argument("--noise", type=float, default=0.01, help="Channel depolarizing noise probability")
    p_verify.set_defaults(func=cmd_verify)

    # attack
    p_attack = subparsers.add_parser("attack", help="Simulate quantum attacks (forgery, replay, mitm)")
    p_attack.add_argument(
        "--type",
        type=str,
        choices=["forgery", "impersonation", "replay", "mitm"],
        default="forgery",
        help="Type of synthetic attack",
    )
    p_attack.add_argument("--samples", type=int, default=256, help="Qubits to simulate")
    p_attack.set_defaults(func=cmd_attack)

    # chsh
    p_chsh = subparsers.add_parser("chsh", help="Evaluate Bell-CHSH inequality channel integrity")
    p_chsh.add_argument("--noise", type=float, default=0.01, help="Channel depolarizing noise")
    p_chsh.set_defaults(func=cmd_chsh)

    # bench
    p_bench = subparsers.add_parser("bench", help="Run full performance and security benchmark")
    p_bench.add_argument("--trials", type=int, default=40, help="Number of attack and genuine trials")
    p_bench.add_argument("--samples", type=int, default=5000, help="Number of benchmark verification qubits")
    p_bench.set_defaults(func=cmd_bench)

    args = parser.parse_args(argv)
    if not args.subcommand:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
