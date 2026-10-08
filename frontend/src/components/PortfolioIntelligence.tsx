import React, { useState, useEffect } from 'react';
import { PortfolioIntelligenceService } from '../services/api';
import ChartEngine from './ChartEngine';
import './PortfolioIntelligence.css';

const PortfolioIntelligence: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  const fetchIntelligence = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await PortfolioIntelligenceService.getAnalysis();
      setData(response);
    } catch (err: any) {
      setError(err.message || "Failed to fetch portfolio intelligence");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntelligence();
  }, []);

  if (loading && !data) {
    return <div className="loading-container">Loading Portfolio Intelligence (this may take a minute)...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <h3>Error loading intelligence</h3>
        <p>{error}</p>
        <button onClick={fetchIntelligence}>Retry</button>
      </div>
    );
  }

  if (!data) return null;

  if (data.status === "BROKER_DISCONNECTED") {
    return (
      <div className="portfolio-intelligence">
        <header className="pi-header">
          <h2>Portfolio Intelligence & Decision Support</h2>
          <div className="pi-actions">
             <button onClick={fetchIntelligence} disabled={loading}>{loading ? 'Reconnecting...' : 'Reconnect to Angel One'}</button>
          </div>
        </header>
        <div className="error-container" style={{marginTop: '2rem'}}>
          <h3>Broker Disconnected</h3>
          <p>{data.reason || "Angel One API connection is currently unavailable."}</p>
          <p>The system is in safe mode and no analysis can be performed until connection is restored.</p>
        </div>
      </div>
    );
  }

  const { portfolio_summary, holdings_analysis, daily_investment_action_plan, data_freshness } = data;

  const groupByAction = (plan: any[]) => {
    const grouped = {
      BUY: [] as any[],
      BUY_MORE: [] as any[],
      HOLD: [] as any[],
      REDUCE: [] as any[],
      SELL: [] as any[],
      WATCH_NO_ACTION: [] as any[]
    };
    if (!plan) return grouped;
    
    plan.forEach(item => {
      if (item.action === 'BUY') grouped.BUY.push(item);
      else if (item.action === 'BUY_MORE') grouped.BUY_MORE.push(item);
      else if (item.action === 'HOLD') grouped.HOLD.push(item);
      else if (item.action === 'REDUCE') grouped.REDUCE.push(item);
      else if (item.action === 'SELL') grouped.SELL.push(item);
      else grouped.WATCH_NO_ACTION.push(item);
    });
    return grouped;
  };

  const actionPlanGrouped = groupByAction(daily_investment_action_plan);

  const renderActionTable = (title: string, items: any[], badgeClass: string) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="action-group">
        <h4 className={`action-title ${badgeClass}`}>{title}</h4>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Action</th>
                <th>Stock</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item: any, i: number) => (
                <tr key={i} onClick={() => setSelectedSymbol(`${item.symbol}`)} style={{cursor:'pointer'}}>
                  <td><span className={`decision-badge ${badgeClass}`}>{item.action.replace('_', ' ')}</span></td>
                  <td><strong>{item.symbol}</strong></td>
                  <td>{item.quantity > 0 ? `${item.quantity} shares` : (item.action === 'HOLD' ? `${item.current_quantity} shares` : '—')}</td>
                  <td>{item.current_price > 0 ? `₹${item.current_price}` : '—'}</td>
                  <td className="reasons-cell">{item.reasons?.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="portfolio-intelligence">
      <header className="pi-header">
        <h2>Portfolio Intelligence & Decision Support</h2>
        <div className="pi-actions">
           <span className="freshness-badge">Data: {data_freshness?.account_data || 'UNKNOWN'}</span>
           <button onClick={fetchIntelligence} disabled={loading}>{loading ? 'Refreshing...' : 'Refresh Analysis'}</button>
        </div>
      </header>

      {/* 1. Portfolio Overview */}
      {portfolio_summary && (
        <section className="pi-section">
          <h3>Portfolio Overview</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="label">Total Value</span>
              <span className="value">₹{portfolio_summary.total_portfolio_value?.toFixed(2)}</span>
            </div>
            <div className="stat-card">
              <span className="label">Invested Value</span>
              <span className="value">₹{portfolio_summary.invested_value?.toFixed(2)}</span>
            </div>
            <div className="stat-card">
              <span className="label">Unrealized P&L</span>
              <span className={`value ${portfolio_summary.unrealized_pnl >= 0 ? 'positive' : 'negative'}`}>
                ₹{portfolio_summary.unrealized_pnl?.toFixed(2)}
              </span>
            </div>
            <div className="stat-card">
              <span className="label">Available Cash</span>
              <span className="value">₹{portfolio_summary.cash_available}</span>
            </div>
            <div className="stat-card">
              <span className="label">Concentration Risk</span>
              <span className={`value risk-${portfolio_summary.concentration?.risk_level?.toLowerCase()}`}>
                {portfolio_summary.concentration?.risk_level} ({portfolio_summary.concentration?.top_asset_percentage?.toFixed(1)}%)
              </span>
            </div>
          </div>
        </section>
      )}

      {/* Chart Engine */}
      {selectedSymbol && (
        <section className="pi-section">
          <ChartEngine symbol={selectedSymbol} />
        </section>
      )}

      {/* 2. TODAY'S INVESTMENT ACTION PLAN */}
      {daily_investment_action_plan && daily_investment_action_plan.length > 0 && (
        <section className="pi-section action-plan-section">
          <h3>TODAY'S INVESTMENT ACTION PLAN</h3>
          <p className="notice">PAPER / DECISION SUPPORT ONLY</p>
          
          {renderActionTable('🟢 BUY', actionPlanGrouped.BUY, 'buy')}
          {renderActionTable('🟢 BUY MORE', actionPlanGrouped.BUY_MORE, 'accumulate')}
          {renderActionTable('🔵 HOLD', actionPlanGrouped.HOLD, 'hold')}
          {renderActionTable('🟠 REDUCE', actionPlanGrouped.REDUCE, 'sell')}
          {renderActionTable('🔴 SELL', actionPlanGrouped.SELL, 'sell')}
          {renderActionTable('🟡 WATCH / NO ACTION', actionPlanGrouped.WATCH_NO_ACTION, 'watch')}

        </section>
      )}

      {/* 3. Current Holdings */}
      {holdings_analysis && holdings_analysis.length > 0 && (
        <section className="pi-section">
          <h3>Current Holdings Analysis</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Stock</th>
                  <th>Qty</th>
                  <th>Avg Price</th>
                  <th>LTP</th>
                  <th>P&L %</th>
                  <th>Technical</th>
                  <th>Fundamental</th>
                  <th>Risk</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {holdings_analysis.map((h: any, i: number) => (
                  <tr key={i} onClick={() => setSelectedSymbol(`${h.symbol}-EQ`)} style={{cursor:'pointer'}} title={h.decision?.reasons?.join('\n')}>
                    <td><strong>{h.symbol}</strong></td>
                    <td>{h.quantity}</td>
                    <td>₹{h.average_price}</td>
                    <td>₹{h.current_price}</td>
                    <td className={h.pnl_percentage >= 0 ? 'positive' : 'negative'}>{h.pnl_percentage}%</td>
                    <td>{h.analysis?.technical_score?.toFixed(1)}</td>
                    <td>{h.analysis?.fundamental_score?.toFixed(1)}</td>
                    <td>{h.analysis?.risk_score?.toFixed(1)}</td>
                    <td>
                      <span className={`decision-badge ${h.decision?.action?.toLowerCase()}`}>
                        {h.decision?.action?.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      
    </div>
  );
};

export default PortfolioIntelligence;
