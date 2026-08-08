import { useState } from 'react'
import { api } from '../api/client'

export default function OrderForm({ tickers, onOrderCreated, isPM }) {
  const [side, setSide] = useState('BUY')
  const [ticker, setTicker] = useState('')
  const [quantity, setQuantity] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.createOrder({ ticker_symbol: ticker, side, quantity: parseFloat(quantity) })
      setQuantity('')
      onOrderCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (!isPM) {
    return (
      <div className="panel">
        <h2>New Order</h2>
        <p className="empty-state">Order entry is a Portfolio Manager action (BRD 6.1).</p>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>New Order</h2>
      <form onSubmit={submit}>
        <div className="side-toggle" style={{ marginBottom: 14 }}>
          <button type="button" className={side === 'BUY' ? 'active buy' : ''} onClick={() => setSide('BUY')}>BUY</button>
          <button type="button" className={side === 'SELL' ? 'active sell' : ''} onClick={() => setSide('SELL')}>SELL</button>
        </div>

        <div className="field-row">
          <label>Security</label>
          <select value={ticker} onChange={e => setTicker(e.target.value)} required>
            <option value="" disabled>Select ticker</option>
            {tickers.map(t => <option key={t.id} value={t.symbol}>{t.symbol} — {t.name}</option>)}
          </select>
        </div>

        <div className="field-row">
          <label>Quantity</label>
          <input type="number" min="0" step="any" value={quantity} onChange={e => setQuantity(e.target.value)} required />
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button className="submit-btn" disabled={busy || !ticker} type="submit">
          {busy ? 'Creating…' : `Create ${side} order`}
        </button>
      </form>
      <p style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 10 }}>
        Don't see your security? Add it from the Securities tab.
      </p>
    </div>
  )
}
