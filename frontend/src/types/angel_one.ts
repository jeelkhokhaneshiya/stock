export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  full_name: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface AngelOneAccountInfo {
  client_id: string;
  name: string;
  email: string | null;
  mobile: string | null;
  pan: string | null;
  exchange_privileges: string[];
  product_privileges: string[];
  broker: string;
}

export interface AngelOneFundsResponse {
  broker: string;
  available_cash: string;
  used_margin: string;
  net_cash: string;
  collateral: string;
  total_pnl: string | null;
  currency: string;
  as_of: string;
}

export interface AngelOneHoldingItem {
  symbol: string;
  exchange: string;
  isin: string | null;
  symbol_token: string | null;
  quantity: string;
  t1_quantity: string;
  average_price: string;
  last_price: string;
  market_value: string;
  pnl: string;
  pnl_percent: string;
  product: string;
}

export interface AngelOneHoldingsResponse {
  broker: string;
  holdings: AngelOneHoldingItem[];
  count: number;
  as_of: string;
}

export interface AngelOnePositionItem {
  symbol: string;
  exchange: string;
  symbol_token: string | null;
  product: string;
  side: string;
  quantity: string;
  average_price: string;
  last_price: string;
  pnl: string;
  pnl_percent: string;
  close_price: string;
}

export interface AngelOnePositionsResponse {
  broker: string;
  positions: AngelOnePositionItem[];
  count: number;
  as_of: string;
}

export interface AngelOneOrderItem {
  broker_order_id: string;
  symbol: string;
  exchange: string;
  side: string;
  order_type: string;
  product: string;
  quantity: string;
  price: string;
  trigger_price: string;
  status: string;
  status_message: string | null;
  filled_quantity: string;
  remaining_quantity: string;
  average_fill_price: string;
  placed_at: string | null;
  updated_at: string | null;
}

export interface AngelOneOrdersResponse {
  broker: string;
  orders: AngelOneOrderItem[];
  count: number;
  as_of: string;
}

export interface BrokerAuthPingResponse {
  provider: string;
  authenticated: boolean;
  status: string;
  message: string;
  live_trading_enabled: boolean;
}
