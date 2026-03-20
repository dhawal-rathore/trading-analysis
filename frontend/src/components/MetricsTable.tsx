interface Props {
  results: any;
}

export default function MetricsTable({ results }: Props) {
  const strategyNames = Object.keys(results)
  
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ 
        width: '100%', 
        borderCollapse: 'collapse', 
        marginTop: '10px',
        backgroundColor: 'white',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <thead>
          <tr style={{ backgroundColor: '#f8f9fa', borderBottom: '2px solid #dee2e6' }}>
            <th style={thStyle}>Strategy</th>
            <th style={thStyle}>Final Equity</th>
            <th style={thStyle}>Return %</th>
            <th style={thStyle}>Max Drawdown %</th>
            <th style={thStyle}>Sharpe Ratio</th>
            <th style={thStyle}>Trades</th>
          </tr>
        </thead>
        <tbody>
          {strategyNames.map(name => {
            const r = results[name]
            return (
              <tr key={name} style={{ borderBottom: '1px solid #eee' }}>
                <td style={tdStyle}><strong>{name}</strong></td>
                <td style={tdStyle}>${r.final_equity.toFixed(2)}</td>
                <td style={{ ...tdStyle, color: r.total_return_pct >= 0 ? 'green' : 'red' }}>
                  {r.total_return_pct.toFixed(2)}%
                </td>
                <td style={tdStyle}>{r.max_drawdown_pct.toFixed(2)}%</td>
                <td style={tdStyle}>{r.sharpe_ratio.toFixed(2)}</td>
                <td style={tdStyle}>{r.trades.length}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

const thStyle = {
  padding: '12px 15px',
  textAlign: 'left' as const,
  fontWeight: 600,
  color: '#495057'
}

const tdStyle = {
  padding: '12px 15px',
  textAlign: 'left' as const,
  color: '#212529'
}
