export default function FillsPanel({ fills }) {
  return (
    <div className="panel">
      <h2>Fills</h2>
      {!fills.length ? (
        <div className="empty-state">No fills yet.</div>
      ) : (
        <table>
          <thead>
            <tr><th>Order</th><th>Qty</th><th>Price</th><th>Broker Ref</th><th>Executed</th></tr>
          </thead>
          <tbody>
            {fills.map(f => (
              <tr key={f.id}>
                <td>{f.order_id.slice(0, 8)}</td>
                <td>{f.quantity}</td>
                <td>{f.price.toFixed(2)}</td>
                <td>{f.broker_fill_ref || '—'}</td>
                <td>{new Date(f.executed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
