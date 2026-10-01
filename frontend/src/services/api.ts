import type { 
  User,
  Token,
  AngelOneAccountInfo,
  AngelOneFundsResponse, 
  AngelOneHoldingsResponse, 
  AngelOnePositionsResponse, 
  AngelOneOrdersResponse, 
  BrokerAuthPingResponse 
} from '../types/angel_one';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const getAuthToken = () => {
  return localStorage.getItem('token');
};

export const setAuthToken = (token: string) => {
  localStorage.setItem('token', token);
};

export const clearAuthToken = () => {
  localStorage.removeItem('token');
};

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function fetchWithAuth<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorMessage = 'An error occurred';
    let data;
    try {
      data = await response.json();
      errorMessage = data.detail || errorMessage;
    } catch {
      // Not JSON
    }
    throw new ApiError(response.status, errorMessage, data);
  }

  return response.json();
}

export const AuthService = {
  login: async (username: string, password: string):Promise<Token> => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = 'Invalid credentials or login failed.';
      try {
        const data = await response.json();
        errorMessage = data.detail || errorMessage;
      } catch {
        // Not JSON
      }
      throw new ApiError(response.status, errorMessage);
    }
    
    return response.json();
  },
  
  me: () => fetchWithAuth<User>('/auth/me'),
};

export const BrokerService = {
  ping: () => fetchWithAuth<BrokerAuthPingResponse>('/broker-monitoring/auth-ping'),
  getAccount: () => fetchWithAuth<AngelOneAccountInfo>('/broker-monitoring/account'),
  getFunds: () => fetchWithAuth<AngelOneFundsResponse>('/broker-monitoring/funds'),
  getHoldings: () => fetchWithAuth<AngelOneHoldingsResponse>('/broker-monitoring/holdings'),
  getPositions: () => fetchWithAuth<AngelOnePositionsResponse>('/broker-monitoring/positions'),
  getOrders: () => fetchWithAuth<AngelOneOrdersResponse>('/broker-monitoring/orders')
};
