import React, { useState, useEffect } from 'react';
import {
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { MarketDataService } from '../services/api';
import { format, parseISO } from 'date-fns';
import './ChartEngine.css';

interface ChartEngineProps {
  symbol: string;
}

const ChartEngine: React.FC<ChartEngineProps> = ({ symbol }) => {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [interval, setInterval] = useState("FIFTEEN_MINUTE");
  const [days, setDays] = useState(5);
  
  // Technical Data State
  const [techData, setTechData] = useState<any>(null);

  useEffect(() => {
    if (!symbol) return;
    fetchData();
  }, [symbol, interval, days]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch OHLC
      const response = await MarketDataService.getOhlc(symbol, interval, days);
      const chartData = response.candles.map((c: any) => {
        const date = parseISO(c.timestamp);
        return {
          timestamp: c.timestamp,
          timeLabel: interval.includes("MINUTE") ? format(date, 'HH:mm') : format(date, 'MMM dd'),
          fullDate: format(date, 'MMM dd yyyy, HH:mm'),
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
          volume: c.volume
        };
      });
      setData(chartData);

      // Fetch Technicals
      const techRes = await MarketDataService.getTechnical(symbol);
      setTechData(techRes);

    } catch (err: any) {
      setError(err.message || 'Failed to fetch chart data');
    } finally {
      setLoading(false);
    }
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const p = payload[0].payload;
      return (
        <div className="custom-tooltip">
          <p className="label">{p.fullDate}</p>
          <p className="intro">Open: ₹{p.open.toFixed(2)}</p>
          <p className="intro">High: ₹{p.high.toFixed(2)}</p>
          <p className="intro">Low: ₹{p.low.toFixed(2)}</p>
          <p className="intro">Close: ₹{p.close.toFixed(2)}</p>
          <p className="desc">Volume: {p.volume.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-engine">
      <div className="chart-controls">
        <h3>{symbol} Chart</h3>
        <div className="controls-group">
          <select value={interval} onChange={(e) => setInterval(e.target.value)}>
            <option value="ONE_MINUTE">1 Minute</option>
            <option value="FIVE_MINUTE">5 Minutes</option>
            <option value="FIFTEEN_MINUTE">15 Minutes</option>
            <option value="ONE_HOUR">1 Hour</option>
            <option value="ONE_DAY">1 Day</option>
          </select>
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={1}>1 Day</option>
            <option value={5}>5 Days</option>
            <option value={30}>1 Month</option>
            <option value={90}>3 Months</option>
            <option value={365}>1 Year</option>
          </select>
          <button onClick={fetchData} disabled={loading}>
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>
      
      {error && <div className="error-text">{error}</div>}
      
      {!loading && data.length === 0 && !error && (
        <div className="empty-message">No chart data available for the selected period.</div>
      )}

      {data.length > 0 && (
        <div className="chart-container">
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={data} margin={{ top: 10, right: 30, left: 20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} vertical={false}/>
              <XAxis dataKey="timeLabel" minTickGap={30} />
              <YAxis 
                yAxisId="price" 
                domain={['auto', 'auto']} 
                orientation="right" 
                tickFormatter={(val) => `₹${val}`}
              />
              <YAxis 
                yAxisId="volume" 
                domain={[0, 'dataMax']} 
                orientation="left" 
                hide 
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              
              <Bar 
                yAxisId="volume" 
                dataKey="volume" 
                fill="#8884d8" 
                opacity={0.3} 
                name="Volume" 
              />
              <Line 
                yAxisId="price" 
                type="monotone" 
                dataKey="close" 
                stroke="#00C49F" 
                dot={false} 
                strokeWidth={2}
                name="Close Price" 
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {techData && techData.status === "SUCCESS" && (
        <div className="technical-panel">
          <h4>Technical Analysis summary</h4>
          <div className="tech-grid">
            <div className="tech-item">
              <span className="label">Trend:</span>
              <span className={`value ${techData.trend.includes("BULLISH") ? "positive" : "negative"}`}>{techData.trend}</span>
            </div>
            <div className="tech-item">
              <span className="label">Momentum:</span>
              <span className="value">{techData.momentum}</span>
            </div>
            <div className="tech-item">
              <span className="label">RSI (14):</span>
              <span className="value">{techData.indicators?.rsi_14?.toFixed(2) || "N/A"}</span>
            </div>
            <div className="tech-item">
              <span className="label">MACD:</span>
              <span className="value">{techData.indicators?.macd?.toFixed(2) || "N/A"}</span>
            </div>
            <div className="tech-item">
              <span className="label">Support:</span>
              <span className="value">₹{techData.support?.toFixed(2) || "N/A"}</span>
            </div>
            <div className="tech-item">
              <span className="label">Resistance:</span>
              <span className="value">₹{techData.resistance?.toFixed(2) || "N/A"}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChartEngine;
