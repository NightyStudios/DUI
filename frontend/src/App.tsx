import { useMemo } from 'react';
import type { CSSProperties } from 'react';

import { GeneratorOverlay, PreviewPanel, SourceEditorOverlay, StudioTopbar } from './studioShell';
import { LessonPage } from './studioRenderer';
import { resolveStudioTheme } from './theme';
import { useStudioController } from './useStudioController';

export default function App(): JSX.Element {
  const { actions, state } = useStudioController();
  const theme = useMemo(() => resolveStudioTheme(state.activeManifest), [state.activeManifest]);

  const appThemeStyle = {
    '--dui-bg': theme.bg,
    '--dui-bg-accent': theme.backgroundAccent,
    '--dui-surface': theme.surface,
    '--dui-surface-muted': theme.surfaceMuted,
    '--dui-border': theme.border,
    '--dui-text': theme.text,
    '--dui-muted': theme.muted,
    '--dui-accent': theme.accent,
    '--dui-accent-soft': theme.accentSoft,
    '--dui-success': theme.success,
    '--dui-warning': theme.warning,
    '--dui-danger': theme.danger,
    '--dui-shadow-soft': theme.shadow,
    '--dui-radius-lg': theme.radiusLg,
    '--dui-radius-md': theme.radiusMd,
    '--dui-radius-sm': theme.radiusSm,
  } as CSSProperties;

  return (
    <div className="studio-root" style={appThemeStyle}>
      <StudioTopbar
        activeSurfaceId={state.activeSurfaceId}
        busyAction={state.busyAction}
        currentRevision={state.currentRevision}
        currentRoute={state.currentRoute}
        dslRevision={state.dslRevision}
        isMenuOpen={state.isMenuOpen}
        onCommit={() => void actions.handleCommit()}
        onOpenDashboard={actions.openDashboard}
        onRefresh={() => void actions.refreshCurrentSurface()}
        onRevert={() => void actions.handleRevert()}
        onSwitchSurface={actions.switchSurface}
        onToggleGenerator={actions.toggleGeneratorEditor}
        onToggleMenu={actions.toggleMenu}
        onToggleSourceEditor={actions.toggleSourceEditor}
        surfaceOptions={state.surfaceOptions}
      />

      <main className="studio-main">
        {state.statusMessage ? <p className="status-message global-message">{state.statusMessage}</p> : null}
        {state.errorMessage ? <p className="error-message global-message">{state.errorMessage}</p> : null}

        {state.currentRoute.kind === 'lesson' ? (
          <LessonPage
            lesson={state.lessonData}
            manifest={state.activeManifest}
            dashboard={state.dashboard}
            loading={state.lessonLoading}
            onBack={actions.openDashboard}
            onOpenLesson={actions.openLesson}
          />
        ) : (
          <PreviewPanel
            activeManifest={state.activeManifest}
            busyAction={state.busyAction}
            dashboard={state.dashboard}
            onOpenLesson={actions.openLesson}
            onToggleSidebar={actions.toggleSidebar}
            previewManifest={state.previewManifest}
            sidebarCollapsed={state.sidebarCollapsed}
          />
        )}
      </main>

      <GeneratorOverlay
        busyAction={state.busyAction}
        isOpen={state.isGeneratorOpen}
        mode={state.mode}
        onClose={actions.closeGeneratorEditor}
        onCommit={() => void actions.handleCommit()}
        onGenerate={() => void actions.handleGenerate()}
        onModeChange={actions.setMode}
        onPromptChange={actions.setPrompt}
        onRevert={() => void actions.handleRevert()}
        onTargetRevisionChange={actions.setTargetRevision}
        prompt={state.prompt}
        sortedRevisions={state.sortedRevisions}
        targetRevision={state.targetRevision}
      />

      <SourceEditorOverlay
        busyAction={state.busyAction}
        isOpen={state.isSourceEditorOpen}
        onClose={actions.closeSourceEditor}
        onParse={() => void actions.handleParseSource()}
        onSetStarterSource={actions.setStarterSource}
        onSourceTextChange={actions.setSourceText}
        sourceText={state.sourceText}
      />
    </div>
  );
}
