import { useEffect, useState } from 'react'
import { unitLabel } from '../mediaMeta.js'

// Progresso numerico per manga (capitoli) e libri (pagine). Aggiorna il backend
// via onChange (che imposta anche lo stato: in lettura / letto in automatico).
function ProgressTracker({ series, onChange }) {
  const type = series.media_type
  const total = series.progress_total || null
  const [value, setValue] = useState(series.progress_current || 0)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setValue(series.progress_current || 0)
  }, [series.progress_current])

  async function commit(next) {
    const clamped = Math.max(0, total ? Math.min(next, total) : next)
    setValue(clamped)
    setSaving(true)
    try {
      await onChange(clamped)
    } finally {
      setSaving(false)
    }
  }

  const unit = unitLabel(type)
  const percent = total ? Math.round((value / total) * 100) : null

  return (
    <div className="progress-tracker">
      <div className="progress-head">
        <span className="progress-label">
          {value}
          {total ? ` / ${total}` : ''} {unit}
          {percent != null ? ` · ${percent}%` : ''}
        </span>
        {saving && <span className="hint">salvo…</span>}
      </div>

      {percent != null && (
        <div className="progress-bar" aria-hidden="true">
          <div className="progress-bar-fill" style={{ width: `${percent}%` }} />
        </div>
      )}

      <div className="progress-controls">
        <button type="button" onClick={() => commit(value - 1)} disabled={value <= 0}>
          −1
        </button>
        <input
          type="number"
          min="0"
          max={total || undefined}
          value={value}
          onChange={(e) => setValue(Number(e.target.value))}
          onBlur={(e) => commit(Number(e.target.value))}
          aria-label={`${unit} completati`}
        />
        <button
          type="button"
          onClick={() => commit(value + 1)}
          disabled={total ? value >= total : false}
        >
          +1
        </button>
        {total && (
          <button type="button" className="progress-done" onClick={() => commit(total)}>
            Segna come completato
          </button>
        )}
      </div>
    </div>
  )
}

export default ProgressTracker
