import { useState } from 'react'
import { api } from '../api/client'

export default function TickerPanel({ tickers, onChanged, canCreate }) {
  const [symbol, setSymbol] = useState('')
  const [name, setName] = useState('')
  const [exchange, setExchange] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await api.createTicker({ symbol, name, exchange: exchange || null })
      setSymbol(''); setName(''); setExchange('')
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 20, gridTemplateColumns: canCreate ? '280px 1fr' : '1fr' }}>
      {canCreate && (
        <div className="panel">
          <h2>Add Security</h2>
          <form onSubmit={submit}>
            <div className="field-row">
              <label>Symbol</label>
              <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} required />
            </div>
            <div className="field-row">
              <label>Name</label>
              <input value={name} onChange={e => setName(e.target.value)} required />
            </div>
            <div className="field-row">
              <label>Exchange</label>
              <input value={exchange} onChange={e => setExchange(e.target.value)} placeholder="e.g. NASDAQ" />
            </div>
            {error && <div className="error-msg">{error}</div>}
            <button className="submit-btn" disabled={busy} type="submit">
              {busy ? 'Adding…' : 'Add security'}
            </button>
          </form>
        </div>
      )}

      <div className="panel">
        <h2>Reference Data</h2>
        {!tickers.length ? (
          <div className="empty-state">No securities yet.</div>
        ) : (
          <table>
            <thead>
              <tr><th>Symbol</th><th>Name</th><th>Exchange</th></tr>
            </thead>
            <tbody>
              {tickers.map(t => (
                <tr key={t.id}>
                  <td>{t.symbol}</td>
                  <td style={{ fontFamily: 'var(--font-ui)' }}>{t.name}</td>
                  <td>{t.exchange || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
