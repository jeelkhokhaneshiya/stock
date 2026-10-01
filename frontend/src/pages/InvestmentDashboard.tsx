import { useEffect, useState } from 'react';
import { InvestmentService } from '../services/investment_api';
import './InvestmentDashboard.css';

const InvestmentDashboard = () => {
    const [watchlist, setWatchlist] = useState<any[]>([]);
    const [portfolio, setPortfolio] = useState<any | null>(null);
    const [symbolToAnalyze, setSymbolToAnalyze] = useState('');
    const [analysisResult, setAnalysisResult] = useState<any | null>(null);

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
                            {portfolio.holdings.map((h: any, i: number) => (
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