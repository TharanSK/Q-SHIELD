/**
 * API client service for communicating with Q-SHIELD FastAPI backend.
 */

const BASE_URL = ''; // Empty string enables relative routing through Vite proxy or FastAPI direct serving

export async function signAndVerify(params) {
  const res = await fetch(`${BASE_URL}/api/sign-and-verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Sign and verify request failed');
  }
  return res.json();
}

export async function runAttack(params) {
  const res = await fetch(`${BASE_URL}/api/attack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'Attack simulation request failed');
  }
  return res.json();
}

export async function evaluateCHSH(params) {
  const res = await fetch(`${BASE_URL}/api/chsh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Network error' }));
    throw new Error(err.detail || 'CHSH evaluation request failed');
  }
  return res.json();
}

export async function getBenchmarkMetrics() {
  const res = await fetch(`${BASE_URL}/api/benchmark`);
  if (!res.ok) {
    throw new Error('Benchmark fetch failed');
  }
  return res.json();
}
