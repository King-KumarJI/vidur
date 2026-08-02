import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { WeeklyPointResponse } from '../services/types'

// Hex values pinned directly (not CSS vars) since Recharts renders SVG
// presentation attributes, which do not resolve custom properties.
const BAR_COLOR = '#3987e5' // sequential blue, step 400 (dataviz skill reference palette)
const GRID_COLOR = '#2c2c2a' // dark gridline (hairline)
const AXIS_COLOR = '#898781' // muted ink

interface WeeklyBarPoint {
  day: string
  date: string
  minutes: number
}

export function WeeklyCodingTimeChart({ points }: { points: WeeklyPointResponse[] }) {
  if (points.length === 0) {
    return <p className="text-sm text-vidur-text-muted">No weekly coding-time data yet for this project.</p>
  }

  const data: WeeklyBarPoint[] = points.map((point) => ({
    day: point.day_of_week.slice(0, 3),
    date: point.date,
    minutes: point.total_minutes,
  }))

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={GRID_COLOR} vertical={false} />
          <XAxis
            dataKey="day"
            stroke={AXIS_COLOR}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: GRID_COLOR }}
            tickLine={false}
          />
          <YAxis
            stroke={AXIS_COLOR}
            tick={{ fill: AXIS_COLOR, fontSize: 12 }}
            axisLine={{ stroke: GRID_COLOR }}
            tickLine={false}
            width={40}
            label={{ value: 'Minutes', angle: -90, position: 'insideLeft', fill: AXIS_COLOR, fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: '#1a1a19', border: '1px solid #2c2c2a', borderRadius: 6, fontSize: 12 }}
            labelStyle={{ color: '#ffffff' }}
            formatter={(value) => [typeof value === 'number' ? `${value.toFixed(0)} min` : String(value), 'Coding time']}
            labelFormatter={(label) => `${label}`}
          />
          <Bar dataKey="minutes" fill={BAR_COLOR} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
