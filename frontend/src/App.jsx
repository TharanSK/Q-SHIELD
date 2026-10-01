import React, { useState } from 'react';
import Navbar from './components/Navbar';
import TeleportationTab from './components/TeleportationTab';
import ThreatSimTab from './components/ThreatSimTab';
import CHSHTab from './components/CHSHTab';
import BenchmarksTab from './components/BenchmarksTab';

export default function App() {
  const [activeTab, setActiveTab] = useState('teleportation');

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col">
      <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === 'teleportation' && <TeleportationTab />}
        {activeTab === 'threats' && <ThreatSimTab />}
        {activeTab === 'chsh' && <CHSHTab />}
        {activeTab === 'benchmarks' && <BenchmarksTab />}
      </main>

      <footer className="border-t border-slate-800/80 bg-[#070b14] py-4 text-center text-xs font-mono text-slate-500">
        Project Q-SHIELD &bull; Quantum Signature Hybrid Integrity and Entanglement-Linked Detection &bull; Non-ML Information-Theoretic Engine
      </footer>
    </div>
  );
}
