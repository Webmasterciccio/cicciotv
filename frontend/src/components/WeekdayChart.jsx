const WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

// Distribuzione degli episodi visti per giorno della settimana (barre semplici).
function WeekdayChart({ data }) {
  const max = Math.max(1, ...data.map((d) => d.count))
  return (
    <div className="weekday-chart">
      {data.map((d) => (
        <div key={d.weekday} className="weekday-col" title={`${d.count} episodi`}>
          <span className="weekday-count">{d.count || ''}</span>
          <div className="weekday-track">
            <div
              className="weekday-bar"
              style={{ height: `${(d.count / max) * 100}%` }}
            />
          </div>
          <span className="weekday-name">{WEEKDAYS[d.weekday] ?? '?'}</span>
        </div>
      ))}
    </div>
  )
}

export default WeekdayChart
