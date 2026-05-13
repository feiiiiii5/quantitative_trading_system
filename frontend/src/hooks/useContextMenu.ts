import { useState, useCallback } from 'react';

export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: () => void;
  danger?: boolean;
  disabled?: boolean;
  type?: 'item';
}

export interface ContextMenuSeparator {
  type: 'separator';
}

export type MenuItem = ContextMenuItem | ContextMenuSeparator;

interface ContextMenuState<T> {
  x: number;
  y: number;
  data: T;
}

export function useContextMenu<T>(items: (data: T) => MenuItem[]) {
  const [state, setState] = useState<ContextMenuState<T> | null>(null);

  const onContextMenu = useCallback((e: React.MouseEvent, data: T) => {
    e.preventDefault();
    setState({ x: e.clientX, y: e.clientY, data });
  }, []);

  const close = useCallback(() => setState(null), []);

  const menuItems = state ? items(state.data) : [];

  return { state, onContextMenu, close, menuItems };
}
