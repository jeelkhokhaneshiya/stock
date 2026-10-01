/// <reference types="@testing-library/jest-dom" />
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import { BrokerService } from '../services/api';

// Mock the API service
vi.mock('../services/api', () => ({
  BrokerService: {
    ping: vi.fn(),
    getAccount: vi.fn(),
    getFunds: vi.fn(),
    getHoldings: vi.fn(),
    getPositions: vi.fn(),
    getOrders: vi.fn(),
  },
  ApiError: class extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
}));

// Mock the Auth Context
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { email: 'test@example.com' },
    logout: vi.fn(),
  }),
}));

describe('Dashboard Component', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders loading state initially', async () => {
    vi.mocked(BrokerService.ping).mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<Dashboard />);
    expect(screen.getByText(/Refreshing\.\.\./i)).toBeInTheDocument();
  });

  it('handles unauthorized API error', async () => {
    const { ApiError } = await import('../services/api');
    vi.mocked(BrokerService.ping).mockRejectedValue(new ApiError(401, 'Unauthorized'));

    render(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText(/Authentication failed or session expired/i)).toBeInTheDocument();
    });
  });

  it('displays successful data and no trading action buttons', async () => {
    vi.mocked(BrokerService.ping).mockResolvedValue({
      provider: 'angel_one',
      authenticated: true,
      status: 'CONNECTED',
      message: 'Auth success',
      live_trading_enabled: false
    });

    vi.mocked(BrokerService.getAccount).mockResolvedValue({
      client_id: 'A1234',
      name: 'John Doe',
      email: 'john@example.com',
      mobile: '9876543210',
      pan: 'ABCDE1234F',
      exchange_privileges: [],
      product_privileges: [],
      broker: 'angel_one'
    });

    vi.mocked(BrokerService.getFunds).mockResolvedValue({
      broker: 'angel_one',
      available_cash: '50000.00',
      used_margin: '1000.00',
      net_cash: '49000.00',
      collateral: '0.00',
      total_pnl: '500.00',
      currency: 'INR',
      as_of: '2023-01-01T00:00:00Z'
    });

    vi.mocked(BrokerService.getHoldings).mockResolvedValue({
      broker: 'angel_one',
      holdings: [],
      count: 0,
      as_of: '2023-01-01T00:00:00Z'
    });

    vi.mocked(BrokerService.getPositions).mockResolvedValue({
      broker: 'angel_one',
      positions: [],
      count: 0,
      as_of: '2023-01-01T00:00:00Z'
    });

    vi.mocked(BrokerService.getOrders).mockResolvedValue({
      broker: 'angel_one',
      orders: [],
      count: 0,
      as_of: '2023-01-01T00:00:00Z'
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Connected')).toBeInTheDocument();
      expect(screen.getByText('₹50000.00')).toBeInTheDocument();
    });

    // Ensure NO trading buttons exist
    const buttons = screen.queryAllByRole('button');
    buttons.forEach(button => {
      const text = button.textContent?.toLowerCase() || '';
      expect(text).not.toMatch(/buy/i);
      expect(text).not.toMatch(/sell/i);
      expect(text).not.toMatch(/cancel/i);
      expect(text).not.toMatch(/modify/i);
    });
    
    // The only button should be Refresh
    const refreshBtn = screen.getByRole('button', { name: /Refresh/i });
    expect(refreshBtn).toBeInTheDocument();
  });

  it('handles partial dashboard failure (funds succeed, holdings fail)', async () => {
    vi.mocked(BrokerService.ping).mockResolvedValue({
      provider: 'angel_one',
      authenticated: true,
      status: 'CONNECTED',
      message: 'Auth success',
      live_trading_enabled: false
    });

    vi.mocked(BrokerService.getAccount).mockResolvedValue({
      client_id: 'A1234',
      name: 'John Doe',
      email: 'john@example.com',
      mobile: '9876543210',
      pan: 'ABCDE1234F',
      exchange_privileges: [],
      product_privileges: [],
      broker: 'angel_one'
    });

    vi.mocked(BrokerService.getFunds).mockResolvedValue({
      broker: 'angel_one',
      available_cash: '50000.00',
      used_margin: '10000.00',
      net_cash: '40000.00',
      collateral: '0.00',
      total_pnl: '150.00',
      currency: 'INR',
      as_of: '2023-10-01'
    });

    vi.mocked(BrokerService.getHoldings).mockRejectedValue(new Error('Network error'));
    vi.mocked(BrokerService.getPositions).mockRejectedValue(new Error('Network error'));
    vi.mocked(BrokerService.getOrders).mockRejectedValue(new Error('Network error'));

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      // Funds should render
      expect(screen.getByText('₹50000.00')).toBeInTheDocument();
      
      // Holdings should show error
      expect(screen.getByText(/Failed to load holdings/i)).toBeInTheDocument();
      // Positions should show error
      expect(screen.getByText(/Failed to load positions/i)).toBeInTheDocument();
      // Orders should show error
      expect(screen.getByText(/Failed to load order book/i)).toBeInTheDocument();
    });
  });
});
