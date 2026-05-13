import { useEffect, useRef, memo } from 'react';
import type { MenuItem } from '@/hooks/useContextMenu';

interface ContextMenuProps {
  x: number;
  y: number;
  items: MenuItem[];
  onClose: () => void;
}

export const ContextMenu = memo(function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [onClose]);

  useEffect(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let adjustX = x;
    let adjustY = y;
    if (rect.right > vw) adjustX = vw - rect.width - 8;
    if (rect.bottom > vh) adjustY = vh - rect.height - 8;
    if (adjustX !== x || adjustY !== y) {
      ref.current.style.left = `${adjustX}px`;
      ref.current.style.top = `${adjustY}px`;
    }
  }, [x, y]);

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        left: x,
        top: y,
        zIndex: 10000,
        minWidth: 180,
        background: 'var(--bg-elevated)',
        border: '1px solid var(--separator)',
        borderRadius: 'var(--r-md)',
        boxShadow: 'var(--shadow-float)',
        padding: '4px 0',
        fontFamily: 'var(--font-sans)',
        fontSize: 13,
      }}
    >
      {items.map((item, i) => {
        if (item.type === 'separator') {
          return (
            <div
              key={`sep-${i}`}
              style={{
                height: 1,
                margin: '4px 0',
                background: 'var(--separator)',
              }}
            />
          );
        }
        return (
          <div
            key={item.label + i}
            onClick={() => {
              if (!item.disabled) {
                item.action();
                onClose();
              }
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 12px',
              cursor: item.disabled ? 'default' : 'pointer',
              color: item.danger ? 'var(--red)' : item.disabled ? 'var(--label-quaternary)' : 'var(--label-primary)',
              opacity: item.disabled ? 0.5 : 1,
              transition: 'background 100ms',
            }}
            onMouseEnter={(e) => {
              if (!item.disabled) (e.currentTarget as HTMLElement).style.background = 'var(--accent-soft)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
          >
            {item.icon && <span style={{ width: 16, textAlign: 'center', fontSize: 12 }}>{item.icon}</span>}
            <span style={{ flex: 1 }}>{item.label}</span>
          </div>
        );
      })}
    </div>
  );
});
