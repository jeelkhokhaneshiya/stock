import React, { useState, useEffect } from 'react';
import type { 
  AngelOneAccountInfo,
  AngelOneFundsResponse, 
  AngelOneHoldingsResponse, 
  AngelOnePositionsResponse, 
  AngelOneOrdersResponse,
  BrokerAuthPingResponse
} from '../types/angel_one';
import { BrokerService, ApiError } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './Dashboard.css';

const Dashboard: React.FC = () => {
  const { logout, user } = useAuth();
  const [status, setStatus] = useState<BrokerAuthPingResponse | null>(null);
  const [account, setAccount] = useState<AngelOneAccountInfo | null>(null);
  const [funds, setFunds] = useState<AngelOneFundsResponse | null>(null);
  const [holdings, setHoldings] = useState<AngelOneHoldingsResponse | null>(null);
  const [positions, setPositions] = useState<AngelOnePositionsResponse | null>(null);
  const [orders, setOrders] = useState<AngelOneOrdersResponse | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectionErrors, setSectionErrors] = useState<Record<string, string>>({});
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // First check connection
      const pingRes = await BrokerService.ping();
      setStatus(pingRes);

      if (pingRes.authenticated) {
        const results = await Promise.allSettled([
          BrokerService.getAccount(),
          BrokerService.getFunds(),
          BrokerService.getHoldings(),
          BrokerService.getPositions(),
          BrokerService.getOrders()
        ]);
        
        const newErrors: Record<string, string> = {};

        if (results[0].status === 'fulfilled') setAccount(results[0].value);
        else newErrors.account = 'Failed to load account details.';

        if (results[1].status === 'fulfilled') setFunds(results[1].value);
        else newErrors.funds = 'Failed to load funds.';

        if (results[2].status === 'fulfilled') setHoldings(results[2].value);
        else newErrors.holdings = 'Failed to load holdings.';

        if (results[3].status === 'fulfilled') setPositions(results[3].value);
        else newErrors.positions = 'Failed to load positions.';

        if (results[4].status === 'fulfilled') setOrders(results[4].value);
        else newErrors.orders = 'Failed to load order book.';

        setSectionErrors(newErrors);
        setLastRefreshed(new Date());
      }
    } catch (err: any) {
      if (err instanceof ApiError) {
        if (err.status === 401 || err.status === 403) {
          setError('Authentication failed or session expired. Please login again.');
        } else if (err.status >= 500) {
          setError('Broker service is currently unavailable. Please try again later.');
        } else {
          setError(err.message || 'An error occurred while fetching data.');
        }
      } else {
        setError('Network error. Cannot reach the server.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h1>Angel One Portfolio</h1>
        <div className="header-actions">
          <a href="/investment" className="btn-secondary" style={{ marginRight: '1rem', color: '#007bff', textDecoration: 'none', fontWeight: 'bold' }}>Investment Engine</a>
          {user && (
            <span className="user-email">{user.email}</span>
          )}
          {lastRefreshed && (
            <span className="last-refreshed">Last refreshed: {lastRefreshed.toLocaleTimeString()}</span>
          )}
          <button 
            className="refresh-button" 
            onClick={fetchData} 
            disabled={loading}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button 
            className="logout-button" 
            onClick={logout}
          >
            Logout
          </button>
        </div>
      </header>

      {error && (
        <div className="error-banner">
          <p>{error}</p>
        </div>
      )}

      {status && (
        <section className="status-section">
          <div className="card">
            <h2>Connection Status</h2>
            <div className="status-details">
              <p><strong>Broker:</strong> {status.provider.toUpperCase()}</p>
              <p>
                <strong>Status:</strong> 
                <span className={`status-badge ${status.authenticated ? 'connected' : 'disconnected'}`}>
                  {status.authenticated ? 'Connected' : 'Disconnected'}
                </span>
              </p>
              <p className="status-message">{status.message}</p>
            </div>
          </div>
        </section>
      )}

      {(account || sectionErrors.account) && (
        <section className="account-section">
          <div className="card">
            <h2>Account Details</h2>
            {sectionErrors.account ? (
              <p className="empty-message error-text">{sectionErrors.account}</p>
            ) : account && (
              <div className="funds-grid">
                <div className="fund-item">
                  <span className="label">Name</span>
                  <span className="value" style={{ fontSize: '1rem' }}>{account.name}</span>
                </div>
                <div className="fund-item">
                  <span className="label">Client ID</span>
                  <span className="value" style={{ fontSize: '1rem' }}>{account.client_id}</span>
                </div>
                <div className="fund-item">
                  <span className="label">Broker</span>
                  <span className="value" style={{ fontSize: '1rem' }}>{account.broker.toUpperCase()}</span>
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {(funds || sectionErrors.funds) && (
        <section className="funds-section">
          <div className="card">
            <h2>Funds & Margin</h2>
            {sectionErrors.funds ? (
              <p className="empty-message error-text">{sectionErrors.funds}</p>
            ) : funds && (
            <div className="funds-grid">
              <div className="fund-item">
                <span className="label">Available Cash</span>
                <span className="value">₹{funds.available_cash}</span>
              </div>
              <div className="fund-item">
                <span className="label">Used Margin</span>
                <span className="value">₹{funds.used_margin}</span>
              </div>
              <div className="fund-item">
                <span className="label">Net Cash</span>
                <span className="value">₹{funds.net_cash}</span>
              </div>
              <div className="fund-item">
                <span className="label">Collateral</span>
                <span className="value">₹{funds.collateral}</span>
              </div>
              {funds.total_pnl && (
                <div className="fund-item">
                  <span className="label">Total P&L</span>
                  <span className={`value ${Number(funds.total_pnl) >= 0 ? 'positive' : 'negative'}`}>
                    ₹{funds.total_pnl}
                  </span>
                </div>
              )}
            </div>
            )}
          </div>
        </section>
      )}

      {(holdings || sectionErrors.holdings) && (
        <section className="holdings-section">
          <div className="card">
            <h2>Holdings {holdings ? `(${holdings.count})` : ''}</h2>
            {sectionErrors.holdings ? (
              <p className="empty-message error-text">{sectionErrors.holdings}</p>
            ) : holdings && holdings.count === 0 ? (
              <p className="empty-message">No holdings found.</p>
            ) : holdings && (
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Qty</th>
                      <th>Avg Price</th>
                      <th>LTP</th>
                      <th>Current Value</th>
                      <th>P&L</th>
                      <th>P&L %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {holdings.holdings.map((h, i) => (
                      <tr key={i}>
                        <td>{h.symbol}</td>
                        <td>{h.quantity}</td>
                        <td>₹{h.average_price}</td>
                        <td>₹{h.last_price}</td>
                        <td>₹{h.market_value}</td>
                        <td className={Number(h.pnl) >= 0 ? 'positive' : 'negative'}>
                          ₹{h.pnl}
                        </td>
                        <td className={Number(h.pnl_percent) >= 0 ? 'positive' : 'negative'}>
                          {h.pnl_percent}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {(positions || sectionErrors.positions) && (
        <section className="positions-section">
          <div className="card">
            <h2>Positions {positions ? `(${positions.count})` : ''}</h2>
            {sectionErrors.positions ? (
              <p className="empty-message error-text">{sectionErrors.positions}</p>
            ) : positions && positions.count === 0 ? (
              <p className="empty-message">No open positions found.</p>
            ) : positions && (
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Product</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Avg Price</th>
                      <th>LTP</th>
                      <th>P&L</th>
                      <th>P&L %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.positions.map((p, i) => (
                      <tr key={i}>
                        <td>{p.symbol}</td>
                        <td>{p.product}</td>
                        <td className={`side-${p.side.toLowerCase()}`}>{p.side}</td>
                        <td>{p.quantity}</td>
                        <td>₹{p.average_price}</td>
                        <td>₹{p.last_price}</td>
                        <td className={Number(p.pnl) >= 0 ? 'positive' : 'negative'}>
                          ₹{p.pnl}
                        </td>
                        <td className={Number(p.pnl_percent) >= 0 ? 'positive' : 'negative'}>
                          {p.pnl_percent}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {(orders || sectionErrors.orders) && (
        <section className="orders-section">
          <div className="card">
            <h2>Order Book {orders ? `(${orders.count})` : ''}</h2>
            <p className="read-only-notice">Read-only view.</p>
            {sectionErrors.orders ? (
              <p className="empty-message error-text">{sectionErrors.orders}</p>
            ) : orders && orders.count === 0 ? (
              <p className="empty-message">No orders found for the current session.</p>
            ) : orders && (
              <div className="table-responsive">
                <table>
                  <thead>
                    <tr>
                      <th>Order ID</th>
                      <th>Symbol</th>
                      <th>Type</th>
                      <th>Side</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th>Status</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.orders.map((o, i) => (
                      <tr key={i}>
                        <td className="order-id">{o.broker_order_id}</td>
                        <td>{o.symbol}</td>
                        <td>{o.order_type}</td>
                        <td className={`side-${o.side.toLowerCase()}`}>{o.side}</td>
                        <td>{o.filled_quantity} / {o.quantity}</td>
                        <td>₹{o.price}</td>
                        <td>
                          <span className={`status-tag status-${o.status.toLowerCase()}`}>
                            {o.status}
                          </span>
                        </td>
                        <td>{o.placed_at ? new Date(o.placed_at).toLocaleTimeString() : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
};

export default Dashboard;
