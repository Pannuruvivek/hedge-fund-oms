const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('oms_token')
}

async function request(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  let payload = body
  if (form) {
    payload = new URLSearchParams(form)
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
  } else if (body) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetch(`${BASE_URL}${path}`, { method, headers, body: payload })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const errBody = await res.json()
      detail = errBody.detail || detail
    } catch (_) {}
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', form: { username, password } }),
  register: (username, password, role) => request('/auth/register', { method: 'POST', body: { username, password, role } }),
  me: () => request('/auth/me'),

  listTickers: () => request('/tickers'),
  createTicker: (payload) => request('/tickers', { method: 'POST', body: payload }),

  listOrders: () => request('/orders'),
  createOrder: (payload) => request('/orders', { method: 'POST', body: payload }),
  cancelOrder: (orderId, reason) => request(`/orders/${orderId}/cancel`, { method: 'POST', body: { reason } }),

  // BRD order lifecycle transitions
  runComplianceCheck: (orderId) => request(`/orders/${orderId}/compliance-check`, { method: 'POST' }),
  sendToTrading: (orderId) => request(`/orders/${orderId}/send-to-trading`, { method: 'POST' }),
  sendToBroker: (orderId) => request(`/orders/${orderId}/send-to-broker`, { method: 'POST' }),
  recordFill: (orderId, payload) => request(`/orders/${orderId}/fills`, { method: 'POST', body: payload }),
  simulateFill: (orderId) => request(`/orders/${orderId}/simulate-fill`, { method: 'POST' }),
  sendToPostTrade: (orderId) => request(`/orders/${orderId}/send-to-post-trade`, { method: 'POST' }),

  listFills: () => request('/fills'),

  listAuditLog: () => request('/audit'),
  listUsers: () => request('/auth/users'),
}

export function saveToken(token) {
  localStorage.setItem('oms_token', token)
}
export function clearToken() {
  localStorage.removeItem('oms_token')
}
export function hasToken() {
  return !!getToken()
}
