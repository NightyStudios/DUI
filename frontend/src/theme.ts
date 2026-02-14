import type { ThemeConfig } from './types';

export function applyTheme(theme: ThemeConfig): void {
  const root = document.documentElement;
  Object.entries(theme.tokens).forEach(([name, value]) => {
    root.style.setProperty(`--ui-${name}`, value);
  });
}
