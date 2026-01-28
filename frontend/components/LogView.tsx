import React, { useEffect, useRef, useMemo, useState } from 'react';
import { LogEntry, MessageSource } from '../types';
import { User, Cpu, Info, Wrench, Eye, Activity, Terminal, AlertTriangle, CheckCircle2, Zap } from 'lucide-react';

interface LogViewProps {
  logs: LogEntry[];
}

export const LogView: React.FC<LogViewProps> = ({ logs }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Check if user is at bottom of scroll
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // Consider "at bottom" if within 50px of bottom
    setIsAtBottom(scrollHeight - scrollTop - clientHeight < 50);
  };

  // Only auto-scroll if user is at bottom
  useEffect(() => {
    if (isAtBottom) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isAtBottom]);

  // Pre-process logs to group atomic motor actions (The "Matrix" cleanup)
  const displayLogs = useMemo(() => {
    const processed: any[] = [];
    let motorGroup: any = null;

    for (const log of logs) {
        const text = log.text.toLowerCase();
        // Check for motor skills to collapse
        const isMotor = (text.includes('drag_mouse') || text.includes('click_at') || text.includes('type_text') || text.includes('wait_seconds')) && log.source === MessageSource.TOOL;
        
        if (isMotor) {
            if (motorGroup) {
                motorGroup.count++;
                motorGroup.latestText = log.text;
                motorGroup.timestamp = log.timestamp;
            } else {
                motorGroup = {
                    id: 'group-' + log.id,
                    timestamp: log.timestamp,
                    source: MessageSource.TOOL,
                    text: "Executing Motor Sequence...",
                    latestText: log.text,
                    count: 1,
                    isGroup: true
                };
                processed.push(motorGroup);
            }
        } else {
            motorGroup = null;
            processed.push(log);
        }
    }
    return processed;
  }, [logs]);

  return (
    <div ref={containerRef} onScroll={handleScroll} className="h-full overflow-y-auto p-4 font-mono text-sm space-y-3 scrollbar-hide">
      {displayLogs.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-gray-600 opacity-30">
           <Terminal className="w-16 h-16 mb-4" />
           <p className="tracking-[0.2em] text-xs">AWAITING UPLINK DATA...</p>
        </div>
      )}
      
      {displayLogs.map((log) => {
        // --- CLASSIFICATION LOGIC ---
        const isUser = log.source === MessageSource.USER;
        // Check "Thought" markers from both legacy and streaming formats
        const isThought = log.text.includes('(Thinking)') || log.text.includes('LLM THOUGHT') || log.source === MessageSource.AGENT && log.text.startsWith('(');
        const isError = log.text.toLowerCase().includes('error') || log.text.includes('BACKEND_OFFLINE') || log.text.includes('Failed');
        const isSystem = log.source === MessageSource.SYSTEM;
        const isVision = log.text.includes('look_at_screen') || log.text.includes('scan_ui_tree') || log.metadata?.type === 'vision_analysis';
        const isGroup = log.isGroup;
        const isTool = log.source === MessageSource.TOOL && !isGroup && !isVision;

        // --- STYLING LOGIC ---
        let borderColor = 'border-gray-800';
        let textColor = 'text-gray-400';
        let bgStyle = '';
        let Icon = Info;

        if (isUser) {
            borderColor = 'border-proxi-accent';
            textColor = 'text-proxi-accent';
            bgStyle = 'bg-proxi-accent/5';
            Icon = User;
        } else if (isThought) {
            borderColor = 'border-cyan-500/50';
            textColor = 'text-cyan-400';
            bgStyle = 'bg-cyan-950/20';
            Icon = Cpu;
        } else if (isError) {
             borderColor = 'border-red-500';
             textColor = 'text-red-400';
             bgStyle = 'bg-red-900/10';
             Icon = AlertTriangle;
        } else if (isSystem) {
             borderColor = 'border-green-500/50';
             textColor = 'text-green-400';
             bgStyle = 'bg-green-900/5';
             Icon = CheckCircle2;
        } else if (isVision) {
            borderColor = 'border-purple-500';
            textColor = 'text-purple-300';
            bgStyle = 'bg-purple-900/20';
            Icon = Eye;
        } else if (isGroup) {
            borderColor = 'border-proxi-warning';
            textColor = 'text-gray-300';
            bgStyle = 'bg-proxi-warning/5';
            Icon = Zap;
        } else if (isTool) {
            borderColor = 'border-gray-600';
            textColor = 'text-gray-400';
            Icon = Wrench;
        }

        return (
          <div key={log.id} className={`relative pl-3 border-l-[3px] ${borderColor} py-2 animate-fade-in ${bgStyle} rounded-r-sm transition-all hover:bg-white/5`}>
            
            {/* Header / Timestamp */}
            <div className="flex items-center gap-2 mb-1.5 opacity-60">
                <span className="text-[10px] font-bold font-mono text-gray-500">
                    {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' })}
                </span>
                <span className={`text-[10px] font-bold uppercase tracking-wider ${
                    isUser ? 'text-proxi-accent' : 
                    isThought ? 'text-cyan-500' :
                    isError ? 'text-red-500' : 
                    isSystem ? 'text-green-500' : 
                    isVision ? 'text-purple-400' : 'text-gray-500'
                }`}>
                    {isGroup ? 'MOTOR_CORTEX' : isVision ? 'VISUAL_CORTEX' : log.source}
                </span>
            </div>

            {/* Content Body */}
            <div className={`text-xs md:text-sm leading-relaxed whitespace-pre-wrap font-mono ${textColor}`}>
                
                {/* 1. MOTOR GROUP VIEW */}
                {isGroup ? (
                    <div className="flex items-center gap-3">
                        <Activity className="w-4 h-4 text-proxi-warning animate-pulse" />
                        <div className="flex-1">
                            <div className="font-bold text-proxi-warning text-xs uppercase tracking-widest">
                                Executing Macro Sequence
                                <span className="ml-2 px-1.5 py-0.5 bg-proxi-warning/20 rounded text-[10px] text-white">
                                    {log.count} STEPS
                                </span>
                            </div>
                            <div className="text-[10px] text-gray-500 mt-1 font-mono truncate max-w-[280px]">
                                &gt; {log.latestText.replace('Core Executing: ', '')}
                            </div>
                        </div>
                    </div>
                ) : 
                
                /* 2. VISION VIEW */
                isVision ? (
                     <div className="flex items-start gap-3">
                        <div className="mt-0.5 relative">
                            <Eye className="w-5 h-5 text-purple-400 animate-pulse" />
                            <div className="absolute inset-0 bg-purple-500 blur-lg opacity-20 animate-pulse"></div>
                        </div>
                        <div>
                             {log.text.includes('Result') ? (
                                 <>
                                    <div className="font-bold text-purple-400 text-xs mb-1">ANALYSIS COMPLETE</div>
                                    <div className="text-purple-200/80 text-xs border-l border-purple-500/30 pl-2">
                                        {log.text.replace(/Result:.*VISION_RESULT:/, '').replace('Result: VISION_RESULT:', '').trim().substring(0, 200)}
                                        {log.text.length > 200 && '...'}
                                    </div>
                                 </>
                             ) : (
                                 <div className="text-xs text-purple-300 italic">Scanning screen buffer...</div>
                             )}
                        </div>
                     </div>
                ) : 
                
                /* 3. THOUGHT VIEW */
                isThought ? (
                     <div className="italic opacity-90 pl-1">
                        <span className="text-cyan-600 mr-2 opacity-50">{'//'}</span>
                        {log.text.replace('(Thinking)', '').replace('LLM THOUGHT:', '').trim()}
                     </div>
                ) : 
                
                /* 4. STANDARD VIEW */
                (
                    <div className="flex gap-2">
                        {isError && <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />}
                        {isSystem && !isError && <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />}
                        <span>{log.text}</span>
                    </div>
                )}
            </div>

            {/* JSON Metadata (Only show for meaningful tools/errors) */}
            {log.metadata && !isGroup && !isVision && !isThought && (
                <div className="mt-2 text-[10px] font-mono text-gray-500 bg-black/40 p-2 rounded border border-white/5 overflow-x-auto opacity-60 hover:opacity-100 transition-opacity">
                     <div className="text-gray-600 text-[9px] uppercase mb-1">Payload Data</div>
                     {JSON.stringify(log.metadata, null, 2).substring(0, 300)}
                </div>
            )}
          </div>
        );
      })}
      <div ref={endRef} />
    </div>
  );
};