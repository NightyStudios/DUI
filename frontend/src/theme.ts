import type { UiManifest } from './types';

export interface StudioThemeTokens {
  bg: string;
  backgroundAccent: string;
  surface: string;
  surfaceMuted: string;
  border: string;
  text: string;
  muted: string;
  accent: string;
  accentSoft: string;
  success: string;
  warning: string;
  danger: string;
  shadow: string;
  radiusLg: string;
  radiusMd: string;
  radiusSm: string;
}

const BASE_THEME: StudioThemeTokens = {
  bg: '#f6f7fb',
  backgroundAccent: 'radial-gradient(circle at 15% 20%, rgba(52, 201, 255, 0.14), transparent 40%), radial-gradient(circle at 85% 10%, rgba(255, 166, 84, 0.18), transparent 38%)',
  surface: '#ffffff',
  surfaceMuted: '#f2f4f8',
  border: '#d6dbe5',
  text: '#13213b',
  muted: '#4f5b73',
  accent: '#0c7bf2',
  accentSoft: '#d9ebff',
  success: '#11845b',
  warning: '#9b6b00',
  danger: '#ba2348',
  shadow: '0 12px 30px rgba(10, 29, 64, 0.12)',
  radiusLg: '20px',
  radiusMd: '14px',
  radiusSm: '10px',
};

const PROFILE_OVERRIDES: Record<string, Partial<StudioThemeTokens>> = {
  minimal: {
    surface: '#fcfcfd',
    surfaceMuted: '#f4f5f8',
    border: '#d1d7df',
    accent: '#2469d8',
  },
  liquid_glass: {
    bg: '#e7f4ff',
    surface: 'rgba(255, 255, 255, 0.66)',
    surfaceMuted: 'rgba(244, 248, 255, 0.7)',
    border: 'rgba(122, 156, 209, 0.44)',
    accent: '#0f63da',
    shadow: '0 20px 34px rgba(23, 65, 128, 0.17)',
  },
};

function coerceToken(value: unknown, fallback: string): string {
  if (typeof value !== 'string') {
    return fallback;
  }
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : fallback;
}

export function resolveStudioTheme(manifest: UiManifest | null): StudioThemeTokens {
  if (!manifest) {
    return BASE_THEME;
  }

  const profileTokens = PROFILE_OVERRIDES[manifest.theme.profile] ?? {};
  const tokens = manifest.theme.tokens ?? {};

  return {
    bg: coerceToken(tokens.bg, profileTokens.bg ?? BASE_THEME.bg),
    backgroundAccent: BASE_THEME.backgroundAccent,
    surface: coerceToken(tokens.surface, profileTokens.surface ?? BASE_THEME.surface),
    surfaceMuted: coerceToken(tokens.surface_container, profileTokens.surfaceMuted ?? BASE_THEME.surfaceMuted),
    border: coerceToken(tokens.outline, profileTokens.border ?? BASE_THEME.border),
    text: coerceToken(tokens.text, profileTokens.text ?? BASE_THEME.text),
    muted: coerceToken(tokens.muted, profileTokens.muted ?? BASE_THEME.muted),
    accent: coerceToken(tokens.accent, profileTokens.accent ?? BASE_THEME.accent),
    accentSoft: coerceToken(tokens.accent_container, profileTokens.accentSoft ?? BASE_THEME.accentSoft),
    success: BASE_THEME.success,
    warning: BASE_THEME.warning,
    danger: BASE_THEME.danger,
    shadow: coerceToken(tokens.shadow, profileTokens.shadow ?? BASE_THEME.shadow),
    radiusLg: coerceToken(tokens.radius, profileTokens.radiusLg ?? BASE_THEME.radiusLg),
    radiusMd: BASE_THEME.radiusMd,
    radiusSm: BASE_THEME.radiusSm,
  };
}
