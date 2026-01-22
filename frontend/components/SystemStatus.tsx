import React from 'react';
import { ShieldCheck, Wifi, Cpu, Database, Eye } from 'lucide-react';

interface SystemStatusProps {
  connected: boolean;
  processing?: boolean;
  analyzing?: boolean;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ connected, processing, analyzing }) => {
  return (
    <div className="grid grid-cols-2 gap-4">
        <div className="bg-proxi-dark border border-proxi-gray rounded p-4 flex flex-col items-center justify-center gap-2">
            <Wifi className={`w-5 h-5 ${connected ? 'text-proxi-success' : 'text-gray-600'}`} />
            <div className="text-xs text-gray-400">UPLINK</div>
            <div className={`text-sm font-bold transition-colors ${
                processing ? 'text-proxi-warning animate-pulse' :
                analyzing ? 'text-proxi-success animate-pulse' :
                connected ? 'text-proxi-success' : 'text-gray-600'
            }`}>
                {processing ? 'PROCESSING' : analyzing ? 'VISUAL_ANALYSIS' : connected ? 'SYSTEM_READY' : 'DISCONNECTED'}
            </div>
        </div>
        
        <div className="bg-proxi-dark border border-proxi-gray rounded p-4 flex flex-col items-center justify-center gap-2">
            {analyzing ? <Eye className="w-5 h-5 text-proxi-success animate-pulse" /> : <Cpu className="w-5 h-5 text-proxi-accent" />}
            <div className="text-xs text-gray-400">MODEL</div>
            <div className={`text-sm font-bold ${analyzing ? 'text-proxi-success' : 'text-proxi-accent'}`}>
                {analyzing ? 'GEMINI_VISION' : 'GEMINI_PRO'}
            </div>
        </div>

        <div className="bg-proxi-dark border border-proxi-gray rounded p-4 flex flex-col items-center justify-center gap-2">
            <Database className="w-5 h-5 text-purple-400" />
            <div className="text-xs text-gray-400">VECTOR STORE</div>
            <div className="text-sm font-bold text-purple-400">READY</div>
        </div>

        <div className="bg-proxi-dark border border-proxi-gray rounded p-4 flex flex-col items-center justify-center gap-2">
            <ShieldCheck className="w-5 h-5 text-white" />
            <div className="text-xs text-gray-400">AUTH</div>
            <div className="text-sm font-bold text-white">GITHUB_OAUTH</div>
        </div>
    </div>
  );
};
