/// <reference types="@testing-library/jest-dom" />
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';
import { AuthProvider } from '../contexts/AuthContext';
import { AuthService } from '../services/api';

// Mock the API service
let mockToken: string | null = null;
vi.mock('../services/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/api')>();
  return {
    ...actual,
    AuthService: {
      login: vi.fn(),
      me: vi.fn(),
    },
    getAuthToken: vi.fn(() => mockToken),
    setAuthToken: vi.fn((t) => { mockToken = t; }),
    clearAuthToken: vi.fn(() => { mockToken = null; }),
  };
});

describe('Login Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockToken = null;
    vi.mocked(AuthService.me).mockRejectedValue(new Error('Unauth'));
  });

  const renderLogin = () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <Login />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('renders login form', () => {
    renderLogin();
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
  });

  it('handles invalid login', async () => {
    const { ApiError } = await import('../services/api');
    vi.mocked(AuthService.login).mockRejectedValue(new ApiError(401, 'Invalid credentials'));

    renderLogin();
    
    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'wrongpass' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText(/Invalid email or password/i)).toBeInTheDocument();
    });
  });

  it('handles successful login and redirects', async () => {
    vi.mocked(AuthService.login).mockResolvedValue({ access_token: 'valid_token', token_type: 'bearer' });
    vi.mocked(AuthService.me).mockResolvedValue({ id: '1', email: 'test@example.com', is_active: true, is_superuser: false, full_name: 'Test' });
    
    renderLogin();

    fireEvent.change(screen.getByLabelText(/Email/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByLabelText(/Password/i), { target: { value: 'correctpass' } });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(AuthService.login).toHaveBeenCalledWith('test@example.com', 'correctpass');
      expect(AuthService.me).toHaveBeenCalled();
    });
  });
});
