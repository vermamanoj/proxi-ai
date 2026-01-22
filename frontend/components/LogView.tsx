import React, { useEffect, useRef } from 'react';
import { LogEntry, MessageSource } from '../types';
import { User, Cpu, Info, Wrench, Eye } from 'lucide-react';

interface LogViewProps {
  logs: LogEntry[];
}

export const LogView: React.FC<LogViewProps> = ({ logs }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="h-full overflow-y-auto p-4 font-mono text-sm space-y-4">
      {logs.length === 0 && (
        <div className="text-gray-500 text-center mt-10 opacity-50">
          <p>NO_DATA_RECEIVED</p>
          <p className="text-xs">Waiting for uplink...</p>
        </div>
      )}
      {logs.map((log) => {
        const isVision = log.metadata?.type === 'vision_analysis';
        
        return (
          <div key={log.id} className="flex gap-3 animate-fade-in">
            <div className="flex-shrink-0 mt-1">
              {log.source === MessageSource.USER && <User className="w-4 h-4 text-proxi-accent" />}
              {log.source === MessageSource.AGENT && (isVision ? <Eye className="w-4 h-4 text-proxi-success" /> : <Cpu className="w-4 h-4 text-purple-400" />)}
              {log.source === MessageSource.SYSTEM && <Info className="w-4 h-4 text-gray-500" />}
              {log.source === MessageSource.TOOL && <Wrench className="w-4 h-4 text-proxi-warning" />}
            </div>
            <div className="flex-1 min-w-0">
               <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-bold uppercase ${
                      log.source === MessageSource.USER ? 'text-proxi-accent' :
                      log.source === MessageSource.AGENT ? 'text-purple-400' :
                      log.source === MessageSource.TOOL ? 'text-proxi-warning' : 'text-gray-500'
                  }`}>
                      {isVision ? 'ARCHITECT_VISION' : log.source}
                  </span>
                  <span className="text-[10px] text-gray-600">
                      {log.timestamp.toLocaleTimeString()}
                  </span>
               </div>
               
               {/* Vision Analysis Block (Architect Mode) */}
               {isVision ? (
                 <div className="mt-1 border-l-2 border-proxi-success pl-3 py-1">
                    <div className="text-xs text-proxi-success mb-2 font-bold tracking-wider">>> ANALYSIS_REPORT: {log.metadata.filename}</div>
                    <div className="text-proxi-success/90 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                        {log.text}
                    </div>
                 </div>
               ) : (
                 <div className="text-gray-300 break-words whitespace-pre-wrap">
                    {log.text}
                 </div>
               )}

               {log.metadata && !isVision && (
                  <div className="mt-2 bg-black/30 border border-gray-800 rounded p-2 text-xs text-gray-400 overflow-x-auto">
                      <pre>{JSON.stringify(log.metadata, null, 2)}</pre>
                  </div>
               )}
            </div>
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
};
