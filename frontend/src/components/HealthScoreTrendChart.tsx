import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// Hex values pinned directly (not CSS vars) since Recharts renders SVG
// presentation attributes, which do not resolve custom properties.
const LINE_COLOR = '#3987e5' // sequential blue, step 400 (dataviz skill reference palette)
const GRID_COLOR = '#2c2c2a' // dark gridline (hairline)
const AXIS_COLOR = '#898781' // muted ink

interface TrendPoint {
  run: number
  healthScore: number
}

export function HealthScoreTrendChart({ healthScores }: { healthScores: number[] }) {
  if (healthScores.length === 0) {
    return <p className="text-sm text-vidur-text-muted">No recorded health-score history yet for this project.</p>
  }

  const data: TrendPoint[] = healthScores.map((healthScore, index) => ({ run: index + 1, healthScore }))

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} vertical={false} />
          <XAxis
            dataKey="run"
            stroke={AXIS_COLOR}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: GRID_COLOR }}
            tickLine={false}
            label={{ value: 'Run #', position: 'insideBottom', offset: -4, fill: AXIS_COLOR, fontSize: 11 }}
          />
          <YAxis
            stroke={AXIS_COLOR}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: GRID_COLOR }}
            tickLine={false}
            domain={[0, 100]}
            width={32}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 6, fontSize: 12 }}
            labelStyle={{ color: '#ffffff' }}
            formatter={(value) => [typeof value === 'number' ? value.toFixed(1) : String(value), 'Health score']}
            labelFormatter={(label) => `Run ${label}`}
          />
          <Line
            type="monotone"
            dataKey="healthScore"
            stroke={LINE_COLOR}
            strokeWidth={2}
            dot={{ r: 3, fill: LINE_COLOR, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
