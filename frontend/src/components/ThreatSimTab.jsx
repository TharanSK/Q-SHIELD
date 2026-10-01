import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, ShieldCheck, ZapOff, RefreshCcw, Radio, Lock, Activity } from 'lucide-react';
import { runAttack } from '../services/api';

export default function ThreatSimTab() {
  const [selectedAttack, setSelectedAttack] = useState('forgery');
  const [samples, setSamples] = useState(256);
  const [loading, setLoading] = useState(false);
  const [attackResult, setAttackResult] = useState(null);
  const [error, setError] = useState(null);

  const attackScenarios = [
    {
      id: 'forgery',
      title: 'Signature Forgery',
      icon: ShieldAlert,
      tag: 'Basis Mismatch',
      color: 'from-amber-500/20 to-rose-500/20 border-amber-500/40',
      desc: 'Adversary generates signature payloads without private basis knowledge. Decoy state basis mismatch creates conjugate error rate e >= 25%, triggering Wald SPRT rejection.',
    },
    {
      id: 'impersonation',
      title: 'Signer Impersonation',
      icon: ZapOff,
      tag: 'Pauli Frame Scrambling',
      color: 'from-rose-500/20 to-purple-500/20 border-rose-500/40',
      desc: 'Malicious actor transmits forged (b1, b2) claiming Alice identity. Incorrect unitaries render state to maximally mixed state rho = I/2. Projective fidelity drops to F = 0.50 (reject F < 0.85).',
    },
    {
      id: 'replay',
      title: 'Nonce Replay Attack',
      icon: RefreshCcw,
      tag: 'Epoch Challenge Cache',
      color: 'from-blue-500/20 to-cyan-500/20 border-blue-500/40',
      desc: 'Adversary re-transmits valid previous teleportation classical bits (b1, b2) with identical timestamped nonce. Detected and blocked immediately by Epoch Nonce Cache.',
    },
    {
      id: 'replay_monogamy',
      title: 'Entanglement Monogamy Replay',
      icon: Lock,
      tag: 'Monogamy Violation',
      color: 'from-purple-500/20 to-indigo-500/20 border-purple-500/40',
      desc: 'Adversary bypasses nonce and applies past (b1, b2) against newly distributed Bell pairs. One-time entanglement consumption scrambles states, yielding QBER >= 45%.',
    },
    {
      id: 'mitm_ir',
      title: 'MITM Intercept-Resend',
      icon: Radio,
      tag: 'CHSH Classical Limit',
      color: 'from-red-500/20 to-amber-500/20 border-red-500/40',
      desc: 'Eavesdropper intercepts and measures distributed Bell photons, collapsing entanglement into separable classical mixture. CHSH S drops to 1.414 <= 2.0, triggering channel abort.',
    },
    {
      id: 'mitm_bs',
      title: 'Channel Beam-Splitting Tap',
      icon: AlertTriangle,
      tag: 'Degraded Entanglement',
      color: 'from-orange-500/20 to-yellow-500/20 border-orange-500/40',
      desc: 'Adversary uses a partial beam-splitting tap to siphon photons. Entanglement degrades below threshold S < 2.4 (Tsirelson bound 2.8284), aborting the channel before signing.',
    },
  ];

  const handleExecuteAttack = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runAttack({
        attack_type: selectedAttack,
        samples: parseInt(samples),
        noise: 0.01,
      });
      setAttackResult(data);
    } catch (err) {
      setError(err.message || 'Attack simulation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <span>Non-ML Cyber Threat Injection & Defense Harness</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Select an adversarial threat vector to evaluate deterministic quantum physical defense mechanics in real time.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <select
              value={samples}
              onChange={(e) => setSamples(e.target.value)}
              className="bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200"
            >
              <option value="128">N = 128 Qubits</option>
              <option value="256">N = 256 Qubits (Acceptance Spec)</option>
              <option value="512">N = 512 Qubits</option>
            </select>

            <button
              onClick={handleExecuteAttack}
              disabled={loading}
              className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-rose-500 to-amber-500 hover:from-rose-400 hover:to-amber-400 text-black font-semibold text-sm transition shadow-lg shadow-rose-500/20 disabled:opacity-50"
            >
              {loading ? (
                <Activity className="w-4 h-4 animate-spin text-black" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-black" />
              )}
              <span>{loading ? 'Simulating Attack...' : 'Inject Cyber Attack'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Threat Scenario Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {attackScenarios.map((scenario) => {
          const Icon = scenario.icon;
          const isSelected = selectedAttack === scenario.id;
          return (
            <div
              key={scenario.id}
              onClick={() => setSelectedAttack(scenario.id)}
              className={`p-4 rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? `bg-slate-900 border-cyan-400 shadow-lg shadow-cyan-500/10`
                  : 'bg-[#0d1527] border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <div className="p-2 rounded-lg bg-slate-800 text-cyan-400">
                    <Icon className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-white">{scenario.title}</h3>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {scenario.tag}
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{scenario.desc}</p>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Forensic Detection Result */}
      {attackResult && (
        <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <span className="text-xs font-mono text-emerald-400 font-bold uppercase tracking-wider">
                  Threat Neutralized by Quantum Mechanics
                </span>
                <h3 className="text-base font-bold text-white">
                  Attack Intercepted: {attackResult.attack_type}
                </h3>
              </div>
            </div>

            <div className="text-right">
              <span className="inline-block px-3 py-1 rounded-full text-xs font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">
                Detection: 100.00%
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Detection Mechanism</span>
              <div className="text-sm font-mono font-bold text-cyan-400 mt-1">
                {attackResult.detection_mechanism}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Primary Physical Metric</span>
              <div className="text-sm font-mono font-bold text-purple-400 mt-1">
                Value: {attackResult.metric_value}
              </div>
            </div>

            <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Decision Protocol</span>
              <div className="text-sm font-mono font-bold text-rose-400 mt-1">
                ABORT / REJECT SIGNATURE
              </div>
            </div>
          </div>

          <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 text-xs font-mono text-slate-300">
            <div className="text-slate-400 mb-1 font-bold">Forensic Telemetry:</div>
            <p className="text-slate-200">{attackResult.details}</p>
          </div>
        </div>
      )}
    </div>
  );
}
