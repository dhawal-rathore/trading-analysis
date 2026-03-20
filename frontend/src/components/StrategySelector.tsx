import { StrategyInfo } from '../App'

interface Props {
  strategies: StrategyInfo[];
  selectedStrategy: string;
  onSelectStrategy: (name: string) => void;
  strategyInfo?: StrategyInfo;
  params: Record<string, any>;
  onChangeParams: (params: Record<string, any>) => void;
}

export default function StrategySelector({ 
  strategies, 
  selectedStrategy, 
  onSelectStrategy, 
  strategyInfo,
  params,
  onChangeParams
}: Props) {
  
  const handleParamChange = (name: string, value: string, type: string) => {
    let parsedValue: any = value;
    if (type === 'int') parsedValue = parseInt(value, 10);
    else if (type === 'float') parsedValue = parseFloat(value);
    
    // Ignore NaN if they cleared the field temporarily
    if (Number.isNaN(parsedValue) && value !== '') return;
    
    onChangeParams({
      ...params,
      [name]: value === '' ? '' : parsedValue
    });
  }

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Strategy</h2>
      
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px' }}>Select Strategy</label>
        <select 
          value={selectedStrategy} 
          onChange={(e) => onSelectStrategy(e.target.value)}
          style={{ width: '100%', padding: '8px', fontSize: '16px' }}
        >
          <option value="" disabled>-- Select a Strategy --</option>
          {strategies.map(s => (
            <option key={s.name} value={s.name}>{s.name}</option>
          ))}
        </select>
      </div>
      
      {strategyInfo && strategyInfo.docstring && (
        <div style={{ fontSize: '14px', color: '#666', marginBottom: '20px', whiteSpace: 'pre-wrap' }}>
          {strategyInfo.docstring}
        </div>
      )}

      {strategyInfo && strategyInfo.params.length > 0 && (
        <div>
          <h3 style={{ fontSize: '16px', borderBottom: '1px solid #ddd', paddingBottom: '5px' }}>Parameters</h3>
          {strategyInfo.params.map(p => (
            <div key={p.name} style={{ marginBottom: '10px' }}>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '3px' }}>
                {p.name} ({p.type}) {p.required && <span style={{color: 'red'}}>*</span>}
              </label>
              <input 
                type={p.type === 'int' || p.type === 'float' ? 'number' : 'text'}
                step={p.type === 'float' ? '0.1' : '1'}
                value={params[p.name] !== undefined ? params[p.name] : ''}
                onChange={(e) => handleParamChange(p.name, e.target.value, p.type)}
                required={p.required}
                style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
