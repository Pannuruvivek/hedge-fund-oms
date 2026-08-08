import { useState } from 'react'
import { api, saveToken } from '../api/client'

export default function Login({ onLoggedIn }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('PORTFOLIO_MANAGER')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === 'register') {
        await api.register(username, password, role)
      }
      const { access_token } = await api.login(username, password)
      saveToken(access_token)
      onLoggedIn()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>OMS Terminal</h1>
        <p className="sub">
          {mode === 'login' ? 'Sign in to manage orders' : 'First user becomes admin'}
        </p>
        <form onSubmit={submit}>
          <div className="field-row">
            <label>Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required autoFocus />
          </div>
          <div className="field-row">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          {mode === 'register' && (
            <div className="field-row">
              <label>Role</label>
              <select value={role} onChange={e => setRole(e.target.value)}>
                <option value="PORTFOLIO_MANAGER">Portfolio Manager</option>
                <option value="TRADER">Trader</option>
                <option value="OPERATIONS">Operations</option>
              </select>
            </div>
          )}
          {error && <div className="error-msg">{error}</div>}
          <button className="submit-btn" disabled={busy} type="submit">
            {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create account & sign in'}
          </button>
        </form>
        <button className="toggle-mode" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Need an account? Register' : 'Already have an account? Sign in'}
        </button>
      </div>
    </div>
  )
}
