import { useState } from 'react'
import { api } from '../api/client'

function FillEntry({ order, onChanged, onError }) {
  const [qty, setQty] = useState('')
  const [price, setPrice] = useState('')
  const [busy, setBusy] = useState(false)
  const remaining = order.quantity - order.filled_quantity

  async function recordFill() {
    setBusy(true)
    try {
      await api.recordFill(order.id, { quantity: parseFloat(qty), price: parseFloat(price) })
      setQty(''); setPrice('')
      onChanged()
    } catch (err) {
      onError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function simulate() {
    setBusy(true)
    try {
      await api.simulateFill(order.id)
      onChanged()
    } catch (err) {
      onError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <input type="number" placeholder="qty" value={qty} onChange={e => setQty(e.target.value)}
             style={{ width: 60 }} max={remaining} min="0" step="any" />
      <input type="number" placeholder="px" value={price} onChange={e => setPrice(e.target.value)}
             style={{ width: 60 }} min="0" step="any" />
      <button className="cancel-link" disabled={busy || !qty || !price} onClick={recordFill}>record</button>
      <button className="cancel-link" disabled={busy} onClick={simulate}>simulate</button>
    </div>
  )
}

export default function OrderTable({ orders, tickerLookup, onChanged, role }) {
  const [error, setError] = useState(null)

  async function act(fn, orderId) {
    setError(null)
    try {
      await fn(orderId)
      onChanged()
    } catch (err) {
      setError(err.message)
    }
  }

  if (!orders.length) {
    return <div className="empty-state">No orders here yet.</div>
  }

  return (
    <div>
      {error && <div className="error-msg" style={{ marginBottom: 8 }}>{error}</div>}
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Side</th>
            <th>Qty</th>
            <th>Filled</th>
            <th>Avg Px</th>
            <th>Status</th>
            <th>Compliance</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          {orders.map(o => (
            <tr key={o.id}>
              <td>{tickerLookup[o.ticker_id] || o.ticker_id.slice(0, 8)}</td>
              <td><span className={`side-pill ${o.side.toLowerCase()}`}>{o.side}</span></td>
              <td>{o.quantity}</td>
              <td>{o.filled_quantity}</td>
              <td>{o.avg_fill_price ? o.avg_fill_price.toFixed(2) : '—'}</td>
              <td>
                <span className="status-pill">
                  <span className={`status-dot ${o.status}`} />
                  {o.status}
                </span>
              </td>
              <td style={{ fontFamily: 'var(--font-ui)', maxWidth: 180, fontSize: 11, color: 'var(--text-muted)' }}>
                {o.compliance_notes || '—'}
              </td>
              <td>
                {role === 'PORTFOLIO_MANAGER' && o.status === 'NEW' && (
                  <button className="cancel-link" onClick={() => act(api.runComplianceCheck, o.id)}>run compliance check</button>
                )}
                {role === 'PORTFOLIO_MANAGER' && o.status === 'OK' && (
                  <button className="cancel-link" onClick={() => act(api.sendToTrading, o.id)}>send to trading</button>
                )}
                {role === 'PORTFOLIO_MANAGER' && ['NEW', 'OK', 'FAIL', 'TRADE_NEW'].includes(o.status) && (
                  <button className="cancel-link" onClick={() => act((id) => api.cancelOrder(id), o.id)} style={{ marginLeft: 8 }}>cancel</button>
                )}
                {role === 'TRADER' && o.status === 'TRADE_NEW' && (
                  <button className="cancel-link" onClick={() => act(api.sendToBroker, o.id)}>send to broker</button>
                )}
                {role === 'TRADER' && o.status === 'EXECUTING' && (
                  <FillEntry order={o} onChanged={onChanged} onError={setError} />
                )}
                {role === 'OPERATIONS' && o.status === 'EXECUTED' && (
                  <button className="cancel-link" onClick={() => act(api.sendToPostTrade, o.id)}>send to post-trade</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
