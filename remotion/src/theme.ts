export const theme = {
  bg: '#07080A',
  panel: '#16181C',
  panelRaised: '#1E2126',
  paper: '#EDE9DF',
  ink: '#16181C',
  border: 'rgba(255,255,255,0.08)',
  borderStrong: 'rgba(255,255,255,0.85)',
  text: '#F4F5F7',
  textDim: 'rgba(244,245,247,0.55)',
  textFaint: 'rgba(244,245,247,0.32)',
  green: '#25D366',
  red: '#FF5A52',
  blue: '#4C8DFF',
  radius: 28,
  sans: "'Inter', system-ui, sans-serif",
  serif: "'Instrument Serif', Georgia, serif",
  hand: "'Caveat', cursive",
  mono: "'Inter', ui-monospace, monospace",
} as const;

/** Área onde o painel de cada cena fica (acima das legendas). */
export const stage = {top: 230, height: 980, width: 940} as const;
