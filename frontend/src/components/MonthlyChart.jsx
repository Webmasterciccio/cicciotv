import { useState } from 'react'

const MONTHS = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic']

function monthLabel(key, showYear) {
  const mm = parseInt(key.slice(5, 7), 10)
  return MONTHS[mm - 1] + (showYear ? ` '${key.slice(2, 4)}` : '')
}

// Grafico a barre a singola serie: episodi visti per mese.
function MonthlyChart({ data }) {
  const [hover, setHover] = useState(null)

  const W = Math.max(320, data.length * 44)
  const H = 190
  const padL = 26
  const padR = 8
  const padT = 18
  const padB = 26
  const innerW = W - padL - padR
  const innerH = H - padT - padB
  const max = Math.max(1, ...data.map((d) => d.count))
  const step = innerW / data.length
  const barW = Math.min(34, step * 0.6)

  // Tacche asse Y: 0 e valore massimo.
  const ticks = [0, max]

  return (
    <div className="chart-wrap">
      <svg
        className="monthly-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Episodi visti per mese"
      >
        {/* griglia orizzontale discreta + valori asse Y */}
        {ticks.map((t) => {
          const y = padT + innerH - (t / max) * innerH
          return (
            <g key={t}>
              <line x1={padL} y1={y} x2={W - padR} y2={y} className="chart-grid" />
              <text x={padL - 6} y={y + 3} className="chart-axis" textAnchor="end">
                {t}
              </text>
            </g>
          )
        })}

        {data.map((d, i) => {
          const barH = (d.count / max) * innerH
          const x = padL + i * step + (step - barW) / 2
          const y = padT + innerH - barH
          const isHover = hover === i
          const showYear = i === 0 || d.month.slice(5, 7) === '01'
          return (
            <g
              key={d.month}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover((h) => (h === i ? null : h))}
            >
              {/* area di hover invisibile piu' ampia della barra */}
              <rect x={padL + i * step} y={padT} width={step} height={innerH} fill="transparent" />
              <rect
                className={`chart-bar${isHover ? ' hover' : ''}`}
                x={x}
                y={y}
                width={barW}
                height={Math.max(barH, d.count > 0 ? 2 : 0)}
                rx="4"
              />
              {isHover && d.count > 0 && (
                <text x={x + barW / 2} y={y - 5} className="chart-value" textAnchor="middle">
                  {d.count}
                </text>
              )}
              <text
                x={padL + i * step + step / 2}
                y={H - 8}
                className="chart-axis"
                textAnchor="middle"
              >
                {monthLabel(d.month, showYear)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export default MonthlyChart
