import React from 'react';
import { ActiveToolState } from '../types';
import { Github, Cloud, Server, Loader2 } from 'lucide-react';

interface ToolStatusProps {
  activeTool: ActiveToolState | null;
}

export const ToolStatus: React.FC<ToolStatusProps> = ({ activeTool }) => {
  if (!activeTool) return null;

  return (
    <div className="bg-proxi-dark border border-proxi-warning/50 rounded-lg p-4 animate-pulse-fast relative overflow-hidden">
        <div className="absolute inset-0 bg-proxi-warning/5" />
        <div className="relative z-10 flex items-center justify-between">
            <div className="flex items-center gap-3">
                {activeTool.name.includes('github') ? <Github className="w-5 h-5 text-proxi-warning" /> :
                 activeTool.name.includes('cloud') ? <Cloud className="w-5 h-5 text-proxi-warning" /> :
                 <Server className="w-5 h-5 text-proxi-warning" />}
                <div>
                    <div className="text-xs text-proxi-warning font-bold uppercase tracking-wider">Executing Tool</div>
                    <div className="text-sm text-white font-mono">{activeTool.name}</div>
                </div>
            </div>
            <Loader2 className="w-5 h-5 text-proxi-warning animate-spin" />
        </div>
    </div>
  );
};