import React, { useState, useEffect } from 'react';
import { Radio, ShieldAlert, CheckCircle2, AlertOctagon, Sliders, Zap } from 'lucide-react';
import { evaluateCHSH } from '../services/api';

export default function CHSHTab() {
  const [noise, setNoise] = useState(0.01);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchCHSH = async (noiseVal) => {
    setLoading(true);
    try {
      const res = await evaluateCHSH({ noise: parseFloat(noiseVal) });
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCHSH(noise);
  }, [noise]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              <span>Bell-CHSH Quantum Channel Entanglement Monitor</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Continuously tests Bell inequality S = |E(a,b) - E(a,b') + E(a',b) + E(a',b')| to detect beam-splitting or quantum channel interception.
            </p>
          </div>

          <div className="w-full md:w-72">
            <div className="flex justify-between text-xs font-mono mb-1">
              <span className="text-slate-400">Channel Noise Level:</span>
              <span className="text-cyan-400 font-bold">{(noise * 100).toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="0.00"
              max="0.30"
              step="0.01"
              value={noise}
              onChange={(e) => setNoise(e.target.value)}
              className="w-full accent-cyan-400"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% (Ideal)</span>
              <span>10%</span>
              <span>20% (Degraded)</span>
              <span>30% (Classical)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main S-Value Gauge & Decision */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-[#0d1527] border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono uppercase text-slate-400">
                Clauser-Horne-Shimony-Holt (CHSH) Parameter S
              </span>
              <span
                className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
                  data.is_secure
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                    : 'bg-rose-950 text-rose-400 border border-rose-800 animate-pulse'
                }`}
              >
                {data.status}
              </span>
            </div>

            <div className="my-6">
              <div className="flex items-baseline space-x-4">
                <span className="text-5xl font-mono font-bold text-white tracking-tight">
                  {data.s_value.toFixed(4)}
                </span>
                <span className="text-xs font-mono text-slate-400">
                  Tsirelson Bound: 2.8284 (2&radic;2)
                </span>
              </div>

              {/* Graphical Bar */}
              <div className="relative mt-4 h-4 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
                {/* 2.0 Classical Limit marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-rose-500 z-10"
                  style={{ left: `${(2.0 / 2.8284) * 100}%` }}
                  title="Classical Limit: S = 2.0"
                ></div>
                {/* 2.4 Secure threshold marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-amber-400 z-10"
                  style={{ left: `${(2.4 / 2.8284) * 100}%` }}
                  title="Secure Threshold: S = 2.4"
                ></div>

                {/* Progress bar */}
                <div
                  className={`h-full transition-all duration-300 ${
                    data.is_secure
                      ? 'bg-gradient-to-r from-cyan-500 to-emerald-400'
                      : 'bg-gradient-to-r from-rose-500 to-amber-500'
                  }`}
                  style={{ width: `${Math.min(100, (data.s_value / 2.8284) * 100)}%` }}
                ></div>
              </div>

              <div className="flex justify-between text-[11px] font-mono text-slate-400 mt-2">
                <span>0.00</span>
                <span className="text-rose-400 font-bold">2.00 (Classical Limit)</span>
                <span className="text-amber-400 font-bold">2.40 (Security Bound)</span>
                <span className="text-emerald-400 font-bold">2.8284 (Tsirelson Max)</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-[#070b14] border border-slate-800 text-xs font-mono">
              <div className="text-slate-300 font-bold mb-1">Channel Policy Directive:</div>
              <p
                className={
                  data.is_secure ? 'text-emerald-400' : 'text-rose-400 font-bold'
                }
              >
                {data.action} —{' '}
                {data.is_secure
                  ? 'Entanglement certified. Quantum signatures can proceed securely.'
                  : 'Channel compromised or noise exceeds security limits. Signature pipeline halted.'}
              </p>
            </div>
          </div>

          {/* Setting Correlations Box */}
          <div className="bg-[#0d1527] border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white mb-1">
                Projective Expectation Values
              </h3>
              <p className="text-xs text-slate-400 mb-4 font-mono">
                Alice: a=0, a'=&pi;/2 | Bob: b=&pi;/4, b'=3&pi;/4
              </p>

              <div className="space-y-3 font-mono text-xs">
                <div className="flex justify-between p-2.5 rounded bg-[#070b14] border border-slate-800">
                  <span className="text-slate-400">E(a, b):</span>
                  <span className="text-cyan-400 font-bold">
                    {data.correlations['E(a,b)']}
                  </span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-[#070b14] border border-slate-800">
                  <span className="text-slate-400">E(a, b'):</span>
                  <span className="text-cyan-400 font-bold">
                    {data.correlations["E(a,b')"]}
                  </span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-[#070b14] border border-slate-800">
                  <span className="text-slate-400">E(a', b):</span>
                  <span className="text-cyan-400 font-bold">
                    {data.correlations["E(a',b)"]}
                  </span>
                </div>
                <div className="flex justify-between p-2.5 rounded bg-[#070b14] border border-slate-800">
                  <span className="text-slate-400">E(a', b'):</span>
                  <span className="text-cyan-400 font-bold">
                    {data.correlations["E(a',b')"]}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 text-[11px] text-slate-400">
              Bell Violation requires S &gt; 2.0. Status:{' '}
              <span className="text-white font-bold">
                {data.is_violated ? 'Violated (Quantum)' : 'Unviolated (Classical)'}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
