import { useEffect, useState, useCallback } from 'react'
import { api, hasToken, clearToken } from './api/client'
import Login from './components/Login'
import OrderForm from './components/OrderForm'
import OrderTable from './components/OrderTable'
import TickerPanel from './components/TickerPanel'
import FillsPanel from './components/FillsPanel'
import AuditPanel from './components/AuditPanel'

export default function App() {
  const [authed, setAuthed] = useState(hasToken())
  const [user, setUser] = useState(null)
  const [tab, setTab] = useState('orders')
  const [tickers, setTickers] = useState([])
  const [orders, setOrders] = useState([])
  const [fills, setFills] = useState([])
  const [auditLog, setAuditLog] = useState([])
  const [error, setError] = useState(null)

  const isPM = user && (user.role === 'PORTFOLIO_MANAGER' || user.role === 'ADMIN')
  const isTrader = user && (user.role === 'TRADER' || user.role === 'ADMIN')
  const isOps = user && (user.role === 'OPERATIONS' || user.role === 'ADMIN')
  const isAdmin = user && user.role === 'ADMIN'
  const canCreateSecurity = user && (user.role === 'PORTFOLIO_MANAGER' || user.role === 'ADMIN')

  const loadCore = useCallback(async () => {
    try {
      const [me, tickerList, orderList] = await Promise.all([
        api.me(), api.listTickers(), api.listOrders(),
      ])
      setUser(me)
      setTickers(tickerList)
      setOrders(orderList)
      setError(null)
    } catch (err) {
      setError(err.message)
      if (String(err.message).toLowerCase().includes('credentials')) {
        clearToken()
        setAuthed(false)
      }
    }
  }, [])

  useEffect(() => { if (authed) loadCore() }, [authed, loadCore])

  useEffect(() => {
    if (!authed) return
    if (tab === 'fills') api.listFills().then(setFills).catch(err => setError(err.message))
    if (tab === 'audit' && isAdmin) api.listAuditLog().then(setAuditLog).catch(err => setError(err.message))
  }, [tab, authed, isAdmin])

  if (!authed) {
    return <Login onLoggedIn={() => setAuthed(true)} />
  }

  const tickerLookup = Object.fromEntries(tickers.map(t => [t.id, t.symbol]))

  const tabs = [
    { id: 'orders', label: 'Orders' },
    { id: 'securities', label: 'Securities' },
    { id: 'fills', label: 'Fills' },
    ...(isAdmin ? [{ id: 'audit', label: 'Audit' }] : []),
  ]

  const roleQueueLabel = {
    PORTFOLIO_MANAGER: 'My Orders',
    TRADER: 'Trading Desk',
    OPERATIONS: 'Post-Trade Queue',
    ADMIN: 'All Orders',
  }[user?.role] || 'Orders'

  return (
    <div className="app-shell">
      <div className="topbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
          <div className="brand">OMS<span>·</span>TERMINAL</div>
          <nav style={{ display: 'flex', gap: 4 }}>
            {tabs.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  background: tab === t.id ? 'var(--surface-raised)' : 'none',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  color: tab === t.id ? 'var(--text)' : 'var(--text-muted)',
                  fontSize: 12,
                  padding: '5px 12px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
        <div className="session">
          {user && (
            <>
              <span>{user.username}</span>
              <span className="role-tag">{user.role.replace('_', ' ')}</span>
            </>
          )}
          <button className="logout-btn" onClick={() => { clearToken(); setAuthed(false) }}>
            Sign out
          </button>
        </div>
      </div>

      <main style={tab === 'orders' && isPM ? undefined : { gridTemplateColumns: '1fr' }}>
        {tab === 'orders' && (
          <>
            {isPM && <OrderForm tickers={tickers} onOrderCreated={loadCore} isPM={isPM} />}
            <div className="panel">
              <h2>{roleQueueLabel}</h2>
              {error && <div className="error-msg">{error}</div>}
              <OrderTable orders={orders} tickerLookup={tickerLookup} onChanged={loadCore} role={user?.role} />
            </div>
          </>
        )}

        {tab === 'securities' && (
          <TickerPanel tickers={tickers} onChanged={loadCore} canCreate={canCreateSecurity} />
        )}

        {tab === 'fills' && <FillsPanel fills={fills} />}

        {tab === 'audit' && isAdmin && <AuditPanel logs={auditLog} />}
      </main>
    </div>
  )
}
