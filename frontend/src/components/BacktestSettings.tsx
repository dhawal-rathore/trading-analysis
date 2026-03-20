interface Props {
  symbol: string;
  onChangeSymbol: (v: string) => void;
  timeframe: string;
  onChangeTimeframe: (v: string) => void;
  start: string;
  onChangeStart: (v: string) => void;
  end: string;
  onChangeEnd: (v: string) => void;
  initialCapital: number;
  onChangeInitialCapital: (v: number) => void;
}

export default function BacktestSettings({
  symbol, onChangeSymbol,
  timeframe, onChangeTimeframe,
  start, onChangeStart,
  end, onChangeEnd,
  initialCapital, onChangeInitialCapital
}: Props) {
  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Settings</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>Symbol</label>
          <input 
            type="text" 
            value={symbol} 
            onChange={e => onChangeSymbol(e.target.value.toUpperCase())}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          />
        </div>
        
        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>Timeframe</label>
          <select 
            value={timeframe} 
            onChange={e => onChangeTimeframe(e.target.value)}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          >
            <option value="1day">1 Day</option>
            <option value="1hr">1 Hour</option>
            <option value="15min">15 Minutes</option>
            <option value="5min">5 Minutes</option>
            <option value="1min">1 Minute</option>
          </select>
        </div>
        
        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>Start Date</label>
          <input 
            type="date" 
            value={start} 
            onChange={e => onChangeStart(e.target.value)}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          />
        </div>
        
        <div>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>End Date</label>
          <input 
            type="date" 
            value={end} 
            onChange={e => onChangeEnd(e.target.value)}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          />
        </div>
        
        <div style={{ gridColumn: '1 / -1' }}>
          <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>Initial Capital ($)</label>
          <input 
            type="number" 
            value={initialCapital} 
            onChange={e => onChangeInitialCapital(Number(e.target.value))}
            style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
          />
        </div>
      </div>
    </div>
  )
}
