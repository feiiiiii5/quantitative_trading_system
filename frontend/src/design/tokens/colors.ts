export const colors = {
  market: {
    rise:      '#FF3B5C',
    riseWeak:  'rgba(255,59,92,0.15)',
    riseDim:   'rgba(255,59,92,0.06)',
    fall:      '#00D9A0',
    fallWeak:  'rgba(0,217,160,0.15)',
    fallDim:   'rgba(0,217,160,0.06)',
    neutral:   'rgba(255,255,255,0.40)',
  },
  depth: {
    0: '#000000',
    1: '#0A0A0F',
    2: '#111118',
    3: '#18181F',
    4: '#1F1F28',
    5: '#26262F',
  } as Record<number, string>,
  accent: {
    primary:   '#0A84FF',
    secondary: '#5AC8FA',
    tertiary:  '#BF5AF2',
    warning:   '#FF9F0A',
    danger:    '#FF453A',
    success:   '#30D158',
  },
  label: {
    primary:   '#ffffff',
    secondary: 'rgba(255,255,255,0.60)',
    tertiary:  'rgba(255,255,255,0.35)',
    quaternary:'rgba(255,255,255,0.20)',
  },
  border: {
    subtle:   'rgba(255,255,255,0.04)',
    default:  'rgba(255,255,255,0.08)',
    emphasis: 'rgba(255,255,255,0.14)',
    accent:   'rgba(10,132,255,0.35)',
  },
} as const;
