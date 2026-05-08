export const CANDLESTICK_STYLE = {
  color: 'transparent',
  color0: '#00e676',
  borderColor: '#ff3b3b',
  borderColor0: '#00e676',
  borderWidth: 1,
} as const;

export const MA_COLORS = {
  MA5: '#2979ff',
  MA10: '#e040fb',
  MA20: '#ffd600',
  MA60: '#1de9b6',
  MA120: '#ff3b3b',
  MA250: '#00e676',
} as const;

export const VOLUME_COLORS = {
  rise: 'rgba(255,59,59,0.35)',
  fall: 'rgba(0,230,118,0.35)',
} as const;

export const TREEMAP_COLOR_RANGE = ['#14532d', '#00e676', '#333345', '#ff3b3b', '#7f1d1d'] as const;

export const CHART_THEME = {
  backgroundColor: '#0d0d1a',
  color: ['#2979ff', '#e040fb', '#ffd600', '#1de9b6', '#ff3b3b', '#00e676', '#ff6d00', '#651fff'],
  textStyle: {
    color: '#55556a',
    fontFamily: 'JetBrains Mono',
  },
  title: {
    textStyle: {
      color: '#f0f0f8',
      fontSize: 13,
      fontWeight: 500,
    },
  },
  legend: {
    textStyle: {
      color: '#55556a',
      fontSize: 10,
    },
  },
  tooltip: {
    backgroundColor: '#111120',
    borderColor: 'rgba(255,255,255,0.15)',
    borderWidth: 1,
    textStyle: {
      color: '#f0f0f8',
      fontSize: 11,
      fontFamily: 'JetBrains Mono',
    },
    axisPointer: {
      lineStyle: {
        color: 'rgba(255,255,255,0.2)',
        width: 0.5,
        type: 'dashed' as const,
      },
      crossStyle: {
        color: 'rgba(255,255,255,0.2)',
        width: 0.5,
        type: 'dashed' as const,
      },
    },
  },
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(255,255,255,0.06)',
      },
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(255,255,255,0.04)',
        type: 'dashed' as const,
      },
    },
    axisLabel: {
      color: '#55556a',
      fontSize: 10,
      fontFamily: 'JetBrains Mono',
    },
  },
  valueAxis: {
    axisLine: {
      lineStyle: {
        color: 'rgba(255,255,255,0.06)',
      },
    },
    splitLine: {
      lineStyle: {
        color: 'rgba(255,255,255,0.04)',
        type: 'dashed' as const,
      },
    },
    axisLabel: {
      color: '#55556a',
      fontSize: 10,
      fontFamily: 'JetBrains Mono',
    },
  },
  candlestick: CANDLESTICK_STYLE,
} as const;
