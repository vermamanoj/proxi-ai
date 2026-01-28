import React, { useEffect, useRef, useState } from 'react';
import { TraceStep } from '../types';
import { User, BrainCircuit, Wrench, Terminal, MessageSquare, ChevronDown, ChevronUp, CheckCircle2, XCircle, Loader2, Monitor } from 'lucide-react';
import { ScreenshotBubble } from './ScreenshotBubble';

interface ChatViewProps {
  trace: TraceStep[];
  isProcessing?: boolean;
}

export const ChatView: React.FC<ChatViewProps> = ({ trace, isProcessing = false }) => {
  const endRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [userScrolledUp, setUserScrolledUp] = useState(false);

  // Track if user has scrolled up (away from bottom)
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setUserScrolledUp(!isNearBottom);
  };

  // Only auto-scroll if user hasn't scrolled up
  useEffect(() => {
    if (!userScrolledUp) {
      endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [trace, userScrolledUp]);

  const toggleToolExpand = (idx: number) => {
    setExpandedTools(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  // Group consecutive tool_call + tool_result pairs
  const groupedTrace = React.useMemo(() => {
    const groups: Array<{ type: 'message' | 'tool_group', items: TraceStep[] }> = [];
    let currentToolGroup: TraceStep[] = [];

    trace.forEach((step, idx) => {
      if (step.step_type === 'tool_call' || step.step_type === 'tool_result') {
        currentToolGroup.push(step);
      } else {
        if (currentToolGroup.length > 0) {
          groups.push({ type: 'tool_group', items: [...currentToolGroup] });
          currentToolGroup = [];
        }
        groups.push({ type: 'message', items: [step] });
      }
    });
    
    if (currentToolGroup.length > 0) {
      groups.push({ type: 'tool_group', items: currentToolGroup });
    }
    
    return groups;
  }, [trace]);

  if (trace.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-600 p-8">
        <div className="w-16 h-16 rounded-full border-2 border-gray-800 flex items-center justify-center mb-4">
          <BrainCircuit className="w-8 h-8 opacity-30" />
        </div>
        <p className="text-sm text-gray-500 text-center">
          Ask Proxi to help with system tasks, desktop automation, or incident response.
        </p>
      </div>
    );
  }

  return (
    <div ref={containerRef} onScroll={handleScroll} className="h-full overflow-y-auto p-4 space-y-4">
      {groupedTrace.map((group, groupIdx) => {
        if (group.type === 'tool_group') {
          // Render collapsed tool group
          const isExpanded = expandedTools.has(groupIdx);
          const toolCalls = group.items.filter(i => i.step_type === 'tool_call');
          const hasResults = group.items.some(i => i.step_type === 'tool_result');
          
          return (
            <div key={groupIdx} className="ml-4">
              <button
                onClick={() => toggleToolExpand(groupIdx)}
                className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-300 transition-colors w-full"
              >
                <div className={`flex items-center gap-1.5 px-2 py-1 rounded bg-gray-900 border border-gray-800 ${hasResults ? 'border-green-900' : 'border-yellow-900'}`}>
                  {hasResults ? (
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                  ) : (
                    <Loader2 className="w-3 h-3 text-yellow-500 animate-spin" />
                  )}
                  <span className="text-gray-400">
                    {toolCalls.map(t => t.content?.toString().split('(')[0] || 'tool').join(', ')}
                  </span>
                  {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </div>
              </button>
              
              {isExpanded && (
                <div className="mt-2 ml-2 space-y-2 border-l border-gray-800 pl-3">
                  {group.items.map((item, idx) => (
                    <div key={idx} className="text-xs">
                      {item.step_type === 'tool_call' ? (
                        <div className="text-yellow-500 font-mono">
                          <Wrench className="w-3 h-3 inline mr-1" />
                          {item.content}
                        </div>
                      ) : (
                        <div className="text-green-400 font-mono bg-black/30 p-2 rounded max-h-32 overflow-y-auto">
                          {typeof item.content === 'string' 
                            ? item.content.substring(0, 500) 
                            : JSON.stringify(item.content).substring(0, 500)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        }

        // Render message
        const step = group.items[0];
        const isUser = step.step_type === 'user_input';
        const isThought = step.step_type === 'llm_thought';
        
        // Filter out plan/goal metadata from thought content for cleaner display
        const filterPlanText = (text: string): string => {
          // Remove PLAN_START...PLAN_END blocks
          let filtered = text.replace(/PLAN_START[\s\S]*?PLAN_END/g, '');
          // Remove GOAL_UPDATE lines
          filtered = filtered.replace(/GOAL_UPDATE:\s*\S+\s+(ACTIVE|COMPLETE|FAILED)[^\n]*/g, '');
          // Clean up extra whitespace
          filtered = filtered.replace(/\n{3,}/g, '\n\n').trim();
          return filtered;
        };
        const isResponse = step.step_type === 'final_response';
        const isVerification = step.step_type === 'verification';
        const isScreenshot = step.step_type === 'status_change' && step.metadata?.screenshot;
        const isSeparator = step.step_type === 'status_change' && step.metadata?.separator;

        // Handle separator between conversations
        if (isSeparator) {
          return (
            <div key={groupIdx} className="flex items-center justify-center py-4">
              <div className="flex-1 h-px bg-gray-800" />
              <span className="px-4 text-xs text-gray-600 uppercase tracking-wider">New Conversation</span>
              <div className="flex-1 h-px bg-gray-800" />
            </div>
          );
        }

        // Handle screenshot messages
        if (isScreenshot) {
          return (
            <ScreenshotBubble
              key={groupIdx}
              imageUrl={step.metadata.screenshot}
              caption={typeof step.content === 'string' ? step.content : undefined}
            />
          );
        }

        return (
          <div
            key={groupIdx}
            className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                isUser
                  ? 'bg-proxi-accent text-black rounded-br-sm'
                  : isThought
                  ? 'bg-purple-900/30 border border-purple-800/50 text-purple-200 rounded-bl-sm'
                  : isVerification
                  ? step.metadata?.status === 'success'
                    ? 'bg-green-900/30 border border-green-800/50 text-green-200'
                    : 'bg-red-900/30 border border-red-800/50 text-red-200'
                  : 'bg-gray-900 border border-gray-800 text-gray-200 rounded-bl-sm'
              }`}
            >
              {/* Icon + Label for non-user messages */}
              {!isUser && (
                <div className="flex items-center gap-2 mb-1 text-xs opacity-70">
                  {isThought && <BrainCircuit className="w-3 h-3" />}
                  {isResponse && <MessageSquare className="w-3 h-3" />}
                  {isVerification && (step.metadata?.status === 'success' ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />)}
                  <span className="uppercase tracking-wider">
                    {isThought ? 'thinking' : isVerification ? 'verification' : 'proxi'}
                  </span>
                </div>
              )}
              
              {/* Content */}
              <div className={`text-sm leading-relaxed ${isThought ? 'italic' : ''}`}>
                {typeof step.content === 'string' 
                  ? (isThought ? filterPlanText(step.content) : step.content)
                  : JSON.stringify(step.content)}
              </div>
            </div>
          </div>
        );
      })}

      {/* Processing indicator */}
      {isProcessing && (
        <div className="flex justify-start">
          <div className="bg-gray-900 border border-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Processing...</span>
            </div>
          </div>
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
};
