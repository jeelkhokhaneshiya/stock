import { getAuthToken } from './api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers
  });
  if (!response.ok) throw new Error('API Error');
  return response.json();
}

export const InvestmentService = {
  getWatchlist: () => fetchWithAuth('/investment/watchlist'),
  analyzeStock: (symbol: string) => fetchWithAuth(`/investment/analyze/${symbol}`),
  getPortfolioAnalysis: () => fetchWithAuth('/investment/portfolio-analysis'),
};