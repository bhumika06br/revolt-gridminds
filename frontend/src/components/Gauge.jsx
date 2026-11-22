// A semi-circle gauge drawn with plain SVG (no extra library needed).
// value: 0-100, color: any CSS color

export default function Gauge({ value, color }) {
  const cx = 110, cy = 110, r = 90;
  const clamped = Math.min(100, Math.max(0, value));
  const angle = Math.PI * (1 - clamped / 100); // 180deg (left) -> 0deg (right)
  const x = cx + r * Math.cos(angle);
  const y = cy - r * Math.sin(angle);

  return (
    <svg viewBox="0 0 220 135" className="gauge" role="img" aria-label={`State of health ${value} percent`}>
      {/* grey background arc */}
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="16" strokeLinecap="round" />
      {/* coloured value arc */}
      {clamped > 0 && (
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${x} ${y}`}
              fill="none" stroke={color} strokeWidth="16" strokeLinecap="round" />
      )}
      <text x={cx} y={cy - 10} textAnchor="middle" className="gauge-value">{value.toFixed(1)}%</text>
      <text x={cx} y={cy + 14} textAnchor="middle" className="gauge-label">State of Health</text>
    </svg>
  );
}
