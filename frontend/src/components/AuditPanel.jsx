export default function AuditPanel({ logs }) {
  return (
    <div className="panel">
      <h2>Audit Log</h2>
      {!logs.length ? (
        <div className="empty-state">No audit entries yet.</div>
      ) : (
        <table>
          <thead>
            <tr><th>Time</th><th>Actor</th><th>Role</th><th>Action</th><th>Detail</th></tr>
          </thead>
          <tbody>
            {logs.map(l => (
              <tr key={l.id}>
                <td>{new Date(l.created_at).toLocaleString()}</td>
                <td>{l.actor_username}</td>
                <td>{l.actor_role}</td>
                <td>{l.action}</td>
                <td style={{ fontFamily: 'var(--font-ui)' }}>{l.detail || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
