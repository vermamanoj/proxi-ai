import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, Circle, Loader2, XCircle, AlertTriangle } from 'lucide-react';
import { TraceStep } from '../types';

interface MissionProgressProps {
  trace: TraceStep[];
  isProcessing: boolean;
  viewMode: 'summary' | 'timeline' | 'full';
  onViewModeChange: (mode: 'summary' | 'timeline' | 'full') => void;
}

interface StepSummary {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  toolName?: string;
  result?: string;
  startIndex: number;
  endIndex: number;
}

export const MissionProgress: React.FC<MissionProgressProps> = ({
  trace,
  isProcessing,
  viewMode,
  onViewModeChange
}) => {
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  // Extract mission goal from first user input
  const missionGoal = useMemo(() => {
    const userInput = trace.find(s => s.step_type === 'user_input');
    if (!userInput) return null;
    const content = typeof userInput.content === 'string' ? userInput.content : '';
    return content.length > 60 ? content.substring(0, 60) + '...' : content;
  }, [trace]);

  // Group trace into logical steps (each tool_call + its result = one step)
  const steps = useMemo((): StepSummary[] => {
    const result: StepSummary[] = [];
    let stepId = 0;

    for (let i = 0; i < trace.length; i++) {
      const item = trace[i];
      
      if (item.step_type === 'tool_call') {
        // Extract tool name from content (format: "tool_name(args)")
        const content = typeof item.content === 'string' ? item.content : '';
        const toolName = content.split('(')[0] || 'action';
        
        // Look ahead for result
        const nextItem = trace[i + 1];
        const hasResult = nextItem?.step_type === 'tool_result';
        const resultContent = hasResult && typeof nextItem.content === 'string' 
          ? nextItem.content.substring(0, 100) 
          : '';

        result.push({
          id: `step-${stepId++}`,
          name: formatToolName(toolName),
          toolName,
          status: hasResult ? 'completed' : (isProcessing ? 'running' : 'pending'),
          result: resultContent,
          startIndex: i,
          endIndex: hasResult ? i + 1 : i
        });

        if (hasResult) i++; // Skip the result since we processed it
      }
    }

    return result;
  }, [trace, isProcessing]);

  // Current step for summary view
  const currentStep = steps.find(s => s.status === 'running') || steps[steps.length - 1];
  const completedCount = steps.filter(s => s.status === 'completed').length;
  const progressPercent = steps.length > 0 ? (completedCount / steps.length) * 100 : 0;

  // Final response for summary
  const finalResponse = useMemo(() => {
    const final = [...trace].reverse().find(s => s.step_type === 'final_response');
    return final ? (typeof final.content === 'string' ? final.content : '') : null;
  }, [trace]);

  if (trace.length === 0) return null;

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl mx-4 mt-4 overflow-hidden shrink-0">
      {/* Header with goal and view toggle */}
      <div className="p-3 border-b border-gray-800 flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="text-xs text-gray-500 uppercase tracking-wider">Mission</div>
          <div className="text-sm text-gray-200 truncate">{missionGoal || (isProcessing ? 'Processing...' : 'Ready')}</div>
        </div>
        
        {/* View mode toggle */}
        <div className="flex gap-1 ml-3">
          {(['summary', 'timeline', 'full'] as const).map(mode => (
            <button
              key={mode}
              onClick={() => onViewModeChange(mode)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                viewMode === mode
                  ? 'bg-proxi-accent/20 text-proxi-accent'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {mode.charAt(0).toUpperCase() + mode.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Progress bar */}
      {steps.length > 0 && (
        <div className="px-3 pt-3">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
            <span>{completedCount} of {steps.length} steps</span>
            {isProcessing && <Loader2 className="w-3 h-3 animate-spin text-proxi-accent" />}
          </div>
          <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-proxi-accent transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Summary View: Just current step and final result */}
      {viewMode === 'summary' && (
        <div className="p-3 max-h-40 overflow-y-auto">
          {currentStep && !finalResponse && (
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-proxi-accent" />
              <span className="text-gray-300">{currentStep.name}</span>
            </div>
          )}
          {finalResponse && (
            <div className="text-sm text-gray-200 mt-2">
              {finalResponse}
            </div>
          )}
        </div>
      )}

      {/* Timeline View: Compact step nodes */}
      {viewMode === 'timeline' && (
        <div className="p-3 space-y-2 max-h-32 sm:max-h-60 overflow-y-auto">
          {steps.map((step, idx) => (
            <div key={step.id}>
              <button
                onClick={() => setExpandedStep(expandedStep === step.id ? null : step.id)}
                className="w-full flex items-center gap-2 text-left hover:bg-gray-800/50 rounded p-1 -m-1 transition-colors"
              >
                {step.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />}
                {step.status === 'running' && <Loader2 className="w-4 h-4 text-yellow-500 animate-spin shrink-0" />}
                {step.status === 'pending' && <Circle className="w-4 h-4 text-gray-600 shrink-0" />}
                {step.status === 'failed' && <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                
                <span className={`text-sm flex-1 ${
                  step.status === 'completed' ? 'text-gray-400' :
                  step.status === 'running' ? 'text-gray-200' : 'text-gray-600'
                }`}>
                  {step.name}
                </span>
                
                {step.status === 'completed' && (
                  <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${
                    expandedStep === step.id ? 'rotate-180' : ''
                  }`} />
                )}
              </button>
              
              {/* Expanded result */}
              {expandedStep === step.id && step.result && (
                <div className="ml-6 mt-1 p-2 bg-black/30 rounded text-xs text-gray-400 font-mono max-h-24 overflow-y-auto">
                  {step.result}
                </div>
              )}
            </div>
          ))}
          
          {/* Final response */}
          {finalResponse && (
            <div className="mt-3 pt-3 border-t border-gray-800">
              <div className="text-sm text-gray-200">{finalResponse}</div>
            </div>
          )}
        </div>
      )}

      {/* Full View: Shows indicator to scroll to full trace below */}
      {viewMode === 'full' && (
        <div className="p-3 text-center text-xs text-gray-500">
          ↓ Full trace shown below ↓
        </div>
      )}
    </div>
  );
};

// Helper: Convert tool_name to readable format
function formatToolName(toolName: string): string {
  return toolName
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}
