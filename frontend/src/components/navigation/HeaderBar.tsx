import React from 'react';
import type { ActiveView } from '../../types/satquery';
import { Radar, Layers, Clock, Sparkles, Sun, Moon, User, Activity, Settings } from 'lucide-react';

interface HeaderBarProps {
  activeView: ActiveView;
  setActiveView: (view: ActiveView) => void;
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  activeDemoId?: string;
  onOpenDemoSelector?: () => void;
  onOpenSettings?: () => void;
  onScrollToWorkflow?: () => void;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  activeView,
  setActiveView,
  theme,
  onToggleTheme,
  onOpenDemoSelector,
  onOpenSettings,
  onScrollToWorkflow
}) => {
  return (
    <header className="h-14 border-b border-sat-border bg-sat-surface/95 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between px-4 sm:px-6 selection:bg-sat-accent/30">
      
      {/* Left: Brand Logo & Orbital Instrument Title */}
      <div className="flex items-center space-x-6">
        <button 
          onClick={() => setActiveView('LANDING')}
          className="flex items-center space-x-3 text-left focus:outline-none group"
        >
          <div className="w-8 h-8 rounded bg-sat-panel border border-sat-borderLight flex items-center justify-center text-sat-accent group-hover:border-sat-accent transition-colors">
            <Radar className="w-4.5 h-4.5 animate-spin" style={{ animationDuration: '12s' }} />
          </div>
          <div>
            <span className="font-display font-bold tracking-widest text-base text-slate-100 dark:text-slate-100 text-slate-900 block leading-none">
              SATQUERY
            </span>
            <span className="font-mono text-xs font-semibold tracking-wider text-sat-dim block mt-0.5 uppercase">
              INTELLIGENCE SYSTEM
            </span>
          </div>
        </button>

        {/* Vertical Separator */}
        <div className="h-5 w-px bg-sat-border hidden md:block" />

        {/* Center Navigation Links */}
        <nav className="hidden md:flex items-center space-x-1.5 font-mono text-xs">
          <button
            onClick={() => setActiveView('LANDING')}
            className={`px-3 py-1.5 rounded text-xs transition-colors ${
              activeView === 'LANDING'
                ? 'bg-sat-panel text-sat-text border border-sat-borderLight font-bold'
                : 'text-sat-muted hover:text-sat-text hover:bg-sat-panel/50 font-medium'
            }`}
          >
            OVERVIEW
          </button>

          <button
            onClick={() => setActiveView('WORKSPACE')}
            className={`px-3.5 py-1.5 rounded text-xs flex items-center space-x-1.5 transition-colors ${
              activeView === 'WORKSPACE'
                ? 'bg-sat-accent text-slate-950 font-bold shadow-sm'
                : 'text-sat-muted hover:text-sat-text hover:bg-sat-panel/50 font-medium'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>WORKSPACE</span>
          </button>

          {onScrollToWorkflow && (
            <button
              onClick={onScrollToWorkflow}
              className="px-3 py-1.5 rounded text-xs flex items-center space-x-1.5 text-sat-muted hover:text-sat-accent hover:bg-sat-panel/50 font-medium transition-colors"
            >
              <Activity className="w-3.5 h-3.5 text-sat-accent" />
              <span>WORKFLOW</span>
            </button>
          )}

          <button
            onClick={() => setActiveView('HISTORY')}
            className={`px-3 py-1.5 rounded text-xs flex items-center space-x-1.5 transition-colors ${
              activeView === 'HISTORY'
                ? 'bg-sat-panel text-sat-text border border-sat-borderLight font-bold'
                : 'text-sat-muted hover:text-sat-text hover:bg-sat-panel/50 font-medium'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>ARCHIVE & HISTORY</span>
          </button>
        </nav>
      </div>

      {/* Right Controls: Preset Demos, System Status, Theme Toggle, Profile */}
      <div className="flex items-center space-x-3 font-mono text-xs">
        {onOpenDemoSelector && (
          <button
            onClick={onOpenDemoSelector}
            className="px-3 py-1.5 rounded bg-sat-panel border border-sat-border text-sat-accent text-xs font-bold flex items-center space-x-1.5 hover:border-sat-accent transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">PRESET DEMOS</span>
          </button>
        )}

        {/* System Ready Badge */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded bg-sat-bg border border-sat-border text-xs">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sat-stable opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-sat-stable"></span>
          </span>
          <span className="text-sat-text font-bold uppercase tracking-wider hidden sm:inline">
            SYSTEM READY
          </span>
        </div>

        {/* Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          className="p-1.5 px-2 rounded bg-sat-bg border border-sat-border text-sat-accent hover:border-sat-accent transition-colors flex items-center space-x-1.5 text-xs font-bold"
        >
          {theme === 'dark' ? (
            <Sun className="w-3.5 h-3.5" />
          ) : (
            <Moon className="w-3.5 h-3.5" />
          )}
          <span className="hidden md:inline uppercase">
            {theme === 'dark' ? 'LIGHT' : 'DARK'}
          </span>
        </button>

        {/* Settings Preferences Button */}
        {onOpenSettings && (
          <button
            onClick={onOpenSettings}
            title="Platform Settings & Preferences"
            className="p-1.5 px-2 rounded bg-sat-bg border border-sat-border text-sat-dim hover:text-sat-accent hover:border-sat-accent transition-colors flex items-center space-x-1.5 text-xs font-bold"
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="hidden md:inline uppercase">SETTINGS</span>
          </button>
        )}

        {/* Operator Profile */}
        <button 
          title="Operator Account"
          className="p-1.5 rounded bg-sat-bg border border-sat-border text-sat-dim hover:text-sat-text transition-colors"
        >
          <User className="w-3.5 h-3.5" />
        </button>
      </div>

    </header>
  );
};
