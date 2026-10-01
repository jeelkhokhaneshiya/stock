import os

FRONTEND_FILES = {
    "frontend/src/pages/InvestmentDashboard.tsx": """
import React, { useEffect, useState } from 'react';
import { InvestmentService } from '../services/investment_api';
import './InvestmentDashboard.css';

const InvestmentDashboard = () => {
    const [watchlist, setWatchlist] = useState([]);
    const [portfolio, setPortfolio] = useState(null);
    const [symbolToAnalyze, setSymbolToAnalyze] = useState('');
    const [analysisResult, setAnalysisResult] = useState(null);

    useEffect(() => {
        InvestmentService.getWatchlist().then(setWatchlist);
        InvestmentService.getPortfolioAnalysis().then(setPortfolio);
    }, []);

    const analyzeStock = async () => {
        if (!symbolToAnalyze) return;
        const result = await InvestmentService.analyzeStock(symbolToAnalyze.toUpperCase());
        setAnalysisResult(result);
    };

    return (
        <div className="investment-dashboard">
            <h1>Investment Intelligence Dashboard</h1>
            
            <section className="portfolio-section">
                <h2>Portfolio Intelligence</h2>
                {portfolio ? (
                    <div className="portfolio-stats">
                        <p>Total Invested: ₹{portfolio.total_invested}</p>
                        <p>Current Value: ₹{portfolio.current_value}</p>
                        <p>P&L: {portfolio.pnl_percent}%</p>
                        <h3>Action Queue</h3>
                        <ul>
                            {portfolio.holdings.map((h, i) => (
                                <li key={i}>
                                    <strong>{h.symbol}</strong> - {h.decision} (Score: {h.investment_score})
                                    <p>Reason: {h.reasons.join(', ')}</p>
                                </li>
                            ))}
                        </ul>
                    </div>
                ) : <p>Loading portfolio...</p>}
            </section>

            <section className="analysis-section">
                <h2>Analyze Company</h2>
                <input 
                    type="text" 
                    value={symbolToAnalyze} 
                    onChange={e => setSymbolToAnalyze(e.target.value)} 
                    placeholder="Enter Symbol (e.g. HDFCBANK)"
                />
                <button onClick={analyzeStock}>Analyze</button>
                
                {analysisResult && (
                    <div className="analysis-result card">
                        <h3>{analysisResult.symbol}</h3>
                        <div className={`decision ${analysisResult.decision.toLowerCase()}`}>
                            {analysisResult.decision}
                        </div>
                        <p>Investment Score: {analysisResult.investment_score}</p>
                        <p>Fundamental: {analysisResult.fundamental_rating}</p>
                        <p>Valuation: {analysisResult.valuation_rating}</p>
                        <p>Technical: {analysisResult.technical_trend}</p>
                        <p>Risk: {analysisResult.risk_level}</p>
                        <p>Reasons: {analysisResult.reasons.join(' | ')}</p>
                    </div>
                )}
            </section>
            
            <section className="watchlist-section">
                <h2>Watchlist</h2>
                <ul>
                    {watchlist.map((w, i) => (
                        <li key={i}>{w.symbol}</li>
                    ))}
                </ul>
            </section>
        </div>
    );
};

export default InvestmentDashboard;
""",

    "frontend/src/services/investment_api.ts": """
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
""",

    "frontend/src/pages/InvestmentDashboard.css": """
.investment-dashboard { padding: 2rem; }
.card { border: 1px solid #ddd; padding: 1rem; border-radius: 8px; margin-top: 1rem; }
.decision { font-weight: bold; padding: 0.5rem; border-radius: 4px; display: inline-block; }
.decision.buy { background-color: #d4edda; color: #155724; }
.decision.sell { background-color: #f8d7da; color: #721c24; }
.decision.hold { background-color: #cce5ff; color: #004085; }
.decision.watchlist { background-color: #fff3cd; color: #856404; }
"""
}

def create_frontend_files():
    for path, content in FRONTEND_FILES.items():
        full_path = os.path.join(os.getcwd(), "..", path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content.strip())
    print("Frontend investment modules created successfully.")

if __name__ == "__main__":
    create_frontend_files()
