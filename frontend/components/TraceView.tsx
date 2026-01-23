
import React, { useEffect, useRef } from 'react';
import { TraceStep } from '../types';
import { User, Cpu, Wrench, ArrowDown, Terminal, MessageSquare } from 'lucide-react';

interface TraceViewProps {
  trace: TraceStep[];
}

export const TraceView: React.FC<TraceViewProps> = ({ trace }) => {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [trace]);

  if (trace.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-600 space-y-2">
        <BrainCircuitIcon className="w-12 h-12 opacity-20" />
        <p className="text-xs font-mono">NEURAL TRACE EMPTY</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-6 font-mono relative">
      {/* Central Line */}
      <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gray-800" />

      <div className="space-y-8 relative">
        {trace.map((step, idx) => (
          <div key={idx} className="relative pl-12 group animate-slide-in-right">
            
            {/* Connector Node */}
            <div className={`absolute left-[26px] top-0 w-3 h-3 rounded-full border-2 transform -translate-x-1/2 mt-1.5 z-10 transition-colors
                ${step.step_type === 'user_input' ? 'border-proxi-accent bg-black' : 
                  step.step_type === 'tool_call' ? 'border-proxi-warning bg-black' :
                  step.step_type === 'tool_result' ? 'border-green-500 bg-green-500/20' :
                  'border-purple-500 bg-black'}
            `} />

            {/* Content Card */}
            <div className={`rounded border p-3 transition-all hover:translate-x-1
                ${step.step_type === 'user_input' ? 'border-proxi-accent/30 bg-proxi-accent/5' : 
                  step.step_type === 'tool_call' ? 'border-proxi-warning/30 bg-proxi-warning/5' :
                  step.step_type === 'tool_result' ? 'border-green-500/30 bg-green-500/5' :
                  'border-purple-500/30 bg-purple-500/5'}
            `}>
                {/* Header */}
                <div className="flex items-center justify-between mb-2 border-b border-white/5 pb-2">
                    <div className="flex items-center gap-2">
                        {step.step_type === 'user_input' && <User className="w-4 h-4 text-proxi-accent" />}
                        {step.step_type === 'tool_call' && <Wrench className="w-4 h-4 text-proxi-warning" />}
                        {step.step_type === 'tool_result' && <Terminal className="w-4 h-4 text-green-500" />}
                        {step.step_type === 'final_response' && <MessageSquare className="w-4 h-4 text-purple-400" />}
                        
                        <span className="text-xs font-bold uppercase tracking-wider text-gray-300">
                            {step.step_type.replace('_', ' ')}
                        </span>
                    </div>
                    {step.metadata && (
                        <div className="text-[10px] text-gray-500">
                           {step.step_type === 'user_input' && step.metadata.model}
                        </div>
                    )}
                </div>

                {/* Body */}
                <div className="text-sm text-gray-300 break-words whitespace-pre-wrap">
                    {typeof step.content === 'string' ? step.content : step.content}
                </div>

                {/* Metadata / Args */}
                {step.metadata && (
                    <div className="mt-2 text-[10px] text-gray-500 font-mono bg-black/40 p-2 rounded overflow-x-auto">
                        {step.step_type === 'tool_call' && step.metadata.args && (
                            <div>
                                <span className="text-proxi-warning">ARGS:</span> {JSON.stringify(step.metadata.args)}
                            </div>
                        )}
                        {step.step_type === 'tool_result' && step.metadata.output && (
                            <div className="max-h-20 overflow-y-auto">
                                <span className="text-green-500">OUTPUT:</span> {step.metadata.output}
                            </div>
                        )}
                        {step.step_type === 'final_response' && (
                             <div>LATENCY: {step.metadata.duration}s</div>
                        )}
                    </div>
                )}
            </div>

            {/* Down Arrow between steps */}
            {idx < trace.length - 1 && (
                <div className="absolute left-6 bottom-[-20px] transform -translate-x-1/2 text-gray-700">
                    <ArrowDown className="w-4 h-4" />
                </div>
            )}
          </div>
        ))}
      </div>
      <div ref={endRef} />
    </div>
  );
};

function BrainCircuitIcon(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 4.5a2.5 2.5 0 0 0-4.96-.46 2.5 2.5 0 0 0-1.98 3 2.5 2.5 0 0 0-1.32 3 2.5 2.5 0 0 0 0 2 2.5 2.5 0 0 0 1.32 3 2.5 2.5 0 0 0 1.98 3 2.5 2.5 0 0 0 4.96-.46 2.5 2.5 0 0 0 5 0 2.5 2.5 0 0 0 4.96.46 2.5 2.5 0 0 0 1.98-3 2.5 2.5 0 0 0 1.32-3 2.5 2.5 0 0 0 0-2 2.5 2.5 0 0 0-1.32-3 2.5 2.5 0 0 0-1.98-3 2.5 2.5 0 0 0-4.96.46A2.5 2.5 0 0 0 12 4.5Z" />
      <path d="M12 16v6" />
      <path d="M9 12h6" />
      <path d="M12 2v6" />
    </svg>
  );
}
