import { useState, useEffect } from 'react'
import StrategySelector from './components/StrategySelector'
import BacktestSettings from './components/BacktestSettings'
import MetricsTable from './components/MetricsTable'
import ResultsChart from './components/ResultsChart'

export interface StrategyParam {
  name: string;
  type: string;
  default: any;
  required: boolean;
}

export interface StrategyInfo {
  name: string;
  params: StrategyParam[];
  docstring: string;
}

function App() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([])
  const [selectedStrategy, setSelectedStrategy] = useState<string>('')
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({})
  
  // Settings
  const [symbol, setSymbol] = useState('SPY')
  const [timeframe, setTimeframe] = useState('1day')
  const [start, setStart] = useState('2022-01-01')
  const [end, setEnd] = useState('2023-01-01')
  const [initialCapital, setInitialCapital] = useState(10000)
  
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/strategies')
      .then(res => res.json())
      .then(data => {
        setStrategies(data)
        if (data.length > 0) {
          setSelectedStrategy(data[0].name)
          
          // Set defaults
          const defaults: Record<string, any> = {}
          data[0].params.forEach((p: StrategyParam) => {
            if (p.default !== null) defaults[p.name] = p.default
          })
          setStrategyParams(defaults)
        }
      })
      .catch(err => {
        console.error("Failed to load strategies", err)
        setError("Failed to load strategies from server. Make sure the backend is running.")
      })
  }, [])

  const handleStrategyChange = (name: string) => {
    setSelectedStrategy(name)
    const stratInfo = strategies.find(s => s.name === name)
    if (stratInfo) {
      const defaults: Record<string, any> = {}
      stratInfo.params.forEach(p => {
        if (p.default !== null) defaults[p.name] = p.default
      })
      setStrategyParams(defaults)
    }
  }

  const runBacktest = async () => {
    setLoading(true)
    setError(null)
    setResults(null)
    
    try {
      const response = await fetch('/api/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          timeframe,
          start,
          end,
          strategy: selectedStrategy,
          strategy_params: strategyParams,
          initial_capital: initialCapital,
          lookback: 50,
          commission_pct: 0.001,
          auto_fetch: true,
          include_benchmark: true
        })
      })
      
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Backtest failed')
      }
      
      setResults(data.results)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const currentStratInfo = strategies.find(s => s.name === selectedStrategy)

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>Trading Backtest Engine</h1>
      
      {error && (
        <div style={{ padding: '15px', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px', marginBottom: '20px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
        <div style={{ flex: 1, padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
          <StrategySelector 
            strategies={strategies}
            selectedStrategy={selectedStrategy}
            onSelectStrategy={handleStrategyChange}
            strategyInfo={currentStratInfo}
            params={strategyParams}
            onChangeParams={setStrategyParams}
          />
        </div>
        
        <div style={{ flex: 1, padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
          <BacktestSettings 
            symbol={symbol} onChangeSymbol={setSymbol}
            timeframe={timeframe} onChangeTimeframe={setTimeframe}
            start={start} onChangeStart={setStart}
            end={end} onChangeEnd={setEnd}
            initialCapital={initialCapital} onChangeInitialCapital={setInitialCapital}
          />
        </div>
      </div>

      <button 
        onClick={runBacktest}
        disabled={loading || !selectedStrategy}
        style={{
          width: '100%',
          padding: '15px',
          fontSize: '18px',
          backgroundColor: loading ? '#ccc' : '#2196F3',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: loading ? 'not-allowed' : 'pointer',
          marginBottom: '30px'
        }}
      >
        {loading ? 'Running Simulation...' : 'Run Backtest'}
      </button>

      {results && (
        <div>
          <h2>Results</h2>
          <MetricsTable results={results} />
          
          <div style={{ marginTop: '40px' }}>
            <ResultsChart results={results} />
          </div>
        </div>
      )}
    </div>
  )
}

export default App
