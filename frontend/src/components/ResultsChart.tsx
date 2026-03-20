import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts'

interface Props {
  results: any;
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#a4de6c', '#d0ed57']

export default function ResultsChart({ results }: Props) {
  
  // Transform raw data into recharts format
  // Recharts wants an array of objects like: { timestamp: '...', Strategy1: 10000, Strategy2: 10000 }
  const { chartData, drawdownData } = useMemo(() => {
    const dataMap: Record<string, any> = {}
    const ddMap: Record<string, any> = {}
    
    const strategyNames = Object.keys(results)
    
    // Process Equity
    strategyNames.forEach(name => {
      const curve = results[name].equity_curve
      let maxEquity = 0
      
      curve.forEach((point: any) => {
        const dt = point[0].split('T')[0] // Just the date part
        const equity = point[1]
        
        // Track for equity chart
        if (!dataMap[dt]) dataMap[dt] = { timestamp: dt }
        dataMap[dt][name] = equity
        
        // Calculate and track for drawdown chart
        if (equity > maxEquity) maxEquity = equity
        const drawdown = maxEquity > 0 ? ((equity - maxEquity) / maxEquity) * 100 : 0
        
        if (!ddMap[dt]) ddMap[dt] = { timestamp: dt }
        ddMap[dt][name] = drawdown
      })
    })
    
    // Sort by date
    const sortedData = Object.values(dataMap).sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    const sortedDd = Object.values(ddMap).sort((a, b) => a.timestamp.localeCompare(b.timestamp))
    
    return { chartData: sortedData, drawdownData: sortedDd }
  }, [results])

  const strategyNames = Object.keys(results)

  return (
    <div>
      <h3 style={{ marginBottom: '10px' }}>Equity Curve ($)</h3>
      <div style={{ width: '100%', height: 400, backgroundColor: 'white', padding: '10px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis 
              dataKey="timestamp" 
              tick={{ fontSize: 12 }} 
              minTickGap={30}
            />
            <YAxis 
              domain={['auto', 'auto']} 
              tickFormatter={(val) => `$${val}`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              formatter={(value: number) => [`$${value.toFixed(2)}`, undefined]}
              labelStyle={{ color: '#666' }}
            />
            <Legend />
            {strategyNames.map((name, i) => (
              <Line 
                key={name} 
                type="stepAfter" // Step chart looks better for trading
                dataKey={name} 
                stroke={COLORS[i % COLORS.length]} 
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <h3 style={{ marginTop: '30px', marginBottom: '10px' }}>Drawdown (%)</h3>
      <div style={{ width: '100%', height: 250, backgroundColor: 'white', padding: '10px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <ResponsiveContainer>
          <AreaChart data={drawdownData} margin={{ top: 10, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
            <XAxis 
              dataKey="timestamp" 
              tick={{ fontSize: 12 }} 
              minTickGap={30}
            />
            <YAxis 
              tickFormatter={(val) => `${val}%`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip 
              formatter={(value: number) => [`${value.toFixed(2)}%`, undefined]}
              labelStyle={{ color: '#666' }}
            />
            <Legend />
            {strategyNames.map((name, i) => (
              <Area 
                key={name} 
                type="stepAfter" 
                dataKey={name} 
                stroke={COLORS[i % COLORS.length]} 
                fill={COLORS[i % COLORS.length]} 
                fillOpacity={0.3}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
