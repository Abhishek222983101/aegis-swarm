// Mirrors the CSS custom properties in index.css — kept in sync manually since
// Three.js materials need JS hex values, not CSS variables.
export const COLORS = {
  ink: '#000000',
  panel: '#121212',
  paper: '#f2f2f0',
  amber: '#ffb800',
  signalGreen: '#00e676',
  signalRed: '#ff3b30',
  signalBlue: '#4da6ff',
  line: '#2c2c2c',
} as const

export const STATUS_COLOR: Record<string, string> = {
  nominal: COLORS.signalGreen,
  degraded: COLORS.amber,
  lost: COLORS.signalRed,
}
