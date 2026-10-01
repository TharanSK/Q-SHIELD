import React, { useState, useEffect } from 'react';
import { Play, CheckCircle2, XCircle, Activity, Key, Sliders, ShieldCheck, Cpu } from 'lucide-react';
import { signAndVerify } from '../services/api';

export default function TeleportationTab() {
  const [message, setMessage] = useState('CONTRACT_SETTLEMENT_HASH_0x9F4A');
  const [samples, setSamples] = useState(128);
  const [noise, setNoise] = useState(0.01);
  const [decoyRatio, setDecoyRatio] = useState(0.5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await signAndVerify({
        message,
        samples: parseInt(samples),
        noise: parseFloat(noise),
        decoy_ratio: parseFloat(decoyRatio),
      });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Verification execution failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleRun();
  }, []);

  return (
    <div className="space-y-6">
      {/* Control Panel & Parameters */}
      <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex items-center space-x-2 pb-4 mb-4 border-b border-slate-800 text-cyan-400">
          <Sliders className="w-5 h-5" />
          <h2 className="text-base font-semibold text-white tracking-wide">
            Quantum Teleportation Signing & Channel Configuration
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-mono text-slate-400 mb-1">
              Message Payload To Sign:
            </label>
            <input
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-sm text-cyan-300 font-mono focus:outline-none focus:border-cyan-500"
              placeholder="Enter message..."
            />
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">
              Carrier Qubits (N): {samples}
            </label>
            <select
              value={samples}
              onChange={(e) => setSamples(e.target.value)}
              className="w-full bg-[#070b14] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            >
              <option value="64">64 Qubits</option>
              <option value="128">128 Qubits</option>
              <option value="256">256 Qubits (Target Spec)</option>
              <option value="512">512 Qubits</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">
              Channel Noise (p): {(noise * 100).toFixed(1)}%
            </label>
            <input
              type="range"
              min="0.00"
              max="0.05"
              step="0.005"
              value={noise}
              onChange={(e) => setNoise(e.target.value)}
              className="w-full accent-cyan-400 mt-2"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% (Ideal)</span>
              <span>2% (Spec Gate)</span>
              <span>5% (Max Noise)</span>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center space-x-4 text-xs font-mono text-slate-400">
            <span>Decoy State Ratio: {(decoyRatio * 100).toFixed(0)}%</span>
            <span>MUBs: Computational Z, Hadamard X, Circular Y</span>
          </div>

          <button
            onClick={handleRun}
            disabled={loading}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-semibold text-sm transition shadow-lg shadow-cyan-500/20 disabled:opacity-50"
          >
            {loading ? (
              <Activity className="w-4 h-4 animate-spin text-black" />
            ) : (
              <Play className="w-4 h-4 fill-black" />
            )}
            <span>{loading ? 'Teleporting & Verifying...' : 'Sign & Verify Teleportation'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-sm flex items-center space-x-3">
          <XCircle className="w-5 h-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Verification Telemetry Cards */}
      {result && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Decision */}
          <div
            className={`border rounded-xl p-4 shadow-lg flex flex-col justify-between ${
              result.is_valid
                ? 'bg-emerald-950/20 border-emerald-800/60'
                : 'bg-rose-950/20 border-rose-800/60'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400 uppercase">Verification Decision</span>
              {result.is_valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <XCircle className="w-5 h-5 text-rose-400" />
              )}
            </div>
            <div className="mt-3">
              <div
                className={`text-2xl font-bold font-mono tracking-wide ${
                  result.is_valid ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {result.decision}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {result.is_valid
                  ? 'Authenticated via Pauli reconstruction'
                  : result.rejection_reason || 'Rejected by physical verification'}
              </p>
            </div>
          </div>

          {/* Card 2: Mean Fidelity */}
          <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400 uppercase">Mean Carrier Fidelity</span>
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold font-mono text-cyan-400">
                {(result.mean_fidelity * 100).toFixed(2)}%
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Theoretical F = 1.0 (Noiseless) | Threshold &ge; 85%
              </p>
            </div>
          </div>

          {/* Card 3: Measured QBER */}
          <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400 uppercase">Measured QBER</span>
              <ShieldCheck className="w-5 h-5 text-purple-400" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold font-mono text-purple-400">
                {(result.qber * 100).toFixed(2)}%
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Channel noise tolerance &lt; 15% | Forgery error &ge; 25%
              </p>
            </div>
          </div>

          {/* Card 4: SPRT Log-Likelihood & Nonce */}
          <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400 uppercase">SPRT LLR / Latency</span>
              <Cpu className="w-5 h-5 text-amber-400" />
            </div>
            <div className="mt-3">
              <div className="text-2xl font-bold font-mono text-amber-400">
                {result.sprt_log_likelihood.toFixed(2)}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Elapsed: {result.elapsed_ms.toFixed(1)} ms ({result.total_qubits} qubits)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quantum Teleportation Architecture Diagram */}
      <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5">
        <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-3">
          Quantum Teleportation Signing Pipeline Mechanics
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80">
            <div className="text-cyan-400 font-bold mb-1">1. Entangled State Dist.</div>
            <p className="text-slate-400 text-[11px]">
              EPR source emits Bell pair |&Phi;+&rang; = 1/&radic;2(|00&rang; + |11&rang;). Qubit A &rarr; Alice, Qubit B &rarr; Bob.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80">
            <div className="text-purple-400 font-bold mb-1">2. MUB Message Encoding</div>
            <p className="text-slate-400 text-[11px]">
              Alice maps signature bits to carrier |&psi;&rang; in random bases: Z {`{|0⟩,|1⟩}`}, X {`{|+⟩,|-⟩}`}, Y {`{|+i⟩,|-i⟩}`}.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80">
            <div className="text-amber-400 font-bold mb-1">3. Joint BSM Measurement</div>
            <p className="text-slate-400 text-[11px]">
              Alice executes BSM on (|&psi;&rang;, A), yielding classical 2-bit token (b1, b2) &isin; {`{00, 01, 10, 11}`}.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-[#070b14] border border-slate-800/80">
            <div className="text-emerald-400 font-bold mb-1">4. Pauli Recovery U</div>
            <p className="text-slate-400 text-[11px]">
              Bob reconstructs state applying U = (&sigma;x^b2) &middot; (&sigma;z^b1). Fidelity F = 1.0 (noiseless).
            </p>
          </div>
        </div>
      </div>

      {/* Live Carrier Stream Sample */}
      {result && result.token_samples && (
        <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Carrier State Teleportation Stream (First {result.token_samples.length} Qubits)
              </h3>
              <p className="text-xs text-slate-400">
                Epoch Nonce: <span className="font-mono text-cyan-400">{result.nonce}</span>
              </p>
            </div>
            <span className="text-xs font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">
              Total Stream: {result.total_qubits} Qubits
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-8 gap-2">
            {result.token_samples.map((tok) => {
              const basisColors = {
                Z: 'border-cyan-500/40 bg-cyan-950/20 text-cyan-300',
                X: 'border-purple-500/40 bg-purple-950/20 text-purple-300',
                Y: 'border-amber-500/40 bg-amber-950/20 text-amber-300',
              };
              return (
                <div
                  key={tok.index}
                  className={`p-2 rounded-lg border text-center font-mono ${
                    basisColors[tok.basis] || 'border-slate-800 bg-slate-900'
                  }`}
                >
                  <div className="text-[10px] text-slate-400 flex justify-between">
                    <span>#{tok.index}</span>
                    <span className="font-bold">{tok.basis}</span>
                  </div>
                  <div className="my-1">
                    <span className="text-xs text-slate-200 font-bold">Bit: {tok.bit}</span>
                    <div className="text-[10px] text-slate-400">
                      ({tok.b1}, {tok.b2})
                    </div>
                  </div>
                  <div className="text-[10px] pt-1 border-t border-slate-800/80">
                    <span
                      className={
                        tok.fidelity >= 0.85
                          ? 'text-emerald-400 font-bold'
                          : 'text-rose-400 font-bold'
                      }
                    >
                      F: {(tok.fidelity * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
