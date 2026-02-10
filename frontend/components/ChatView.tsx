import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { TraceStep } from '../types';
import { User, BrainCircuit, Wrench, Terminal, MessageSquare, ChevronDown, ChevronUp, CheckCircle2, XCircle, Loader2, Monitor } from 'lucide-react';
import { ScreenshotBubble } from './ScreenshotBubble';
import { EvidenceCard, parseEvidenceFromMessage } from './EvidenceCard';
import { RenderContent } from './RenderContent';
import { MermaidDiagram } from './MermaidDiagram';

interface ChatViewProps {
  trace: TraceStep[];
  isProcessing?: boolean;
  debugMode?: boolean;
}

/**
 * Detect unfenced mermaid syntax in content and wrap it in ```mermaid fences.
 * LLMs often output raw mermaid (flowchart TD, graph TD, etc.) without code fences.
 */
function wrapUnfencedMermaid(content: string): string {
  // Already has fenced mermaid - skip
  if (content.includes('```mermaid')) return content;

  // Mermaid diagram start keywords
  const mermaidStartRe = /^(graph\s+(TD|TB|BT|LR|RL)|flowchart\s+(TD|TB|BT|LR|RL)|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|mindmap)/m;
  const match = mermaidStartRe.exec(content);
  if (!match || match.index === undefined) return content;

  const before = content.slice(0, match.index);
  const fromStart = content.slice(match.index);
  const lines = fromStart.split('\n');

  // Mermaid-like line: indented, arrows, style, subgraph, end, %%, classDef, empty, or node defs
  const isMermaidLine = (line: string): boolean => {
    const t = line.trim();
    if (t === '') return true; // blank lines inside block
    if (t.startsWith('%%')) return true;
    if (/^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|mindmap)\b/.test(t)) return true;
    if (/^(subgraph|end)\b/.test(t)) return true;
    if (/^(style|classDef|class)\s/.test(t)) return true;
    if (/-->|---|\-\.\->|==>|--x|--o|\|/.test(t)) return true;
    if (/^\w[\w_]*[\[\(\{<]/.test(t)) return true; // node definition
    if (/^\s+\w/.test(line)) return true; // indented content
    return false;
  };

  // Walk lines to find where mermaid ends
  let endIdx = lines.length;
  for (let i = 1; i < lines.length; i++) {
    if (!isMermaidLine(lines[i])) {
      // Trim trailing blank lines from the block
      while (endIdx > i && lines[endIdx - 1].trim() === '') endIdx--;
      endIdx = i;
      break;
    }
  }

  const mermaidBlock = lines.slice(0, endIdx).join('\n');
  const after = lines.slice(endIdx).join('\n');

  return `${before}\`\`\`mermaid\n${mermaidBlock}\n\`\`\`\n${after}`;
}

export const ChatView: React.FC<ChatViewProps> = ({ trace, isProcessing = false, debugMode = false }) => {
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

  // Filter trace based on debug mode
  const filteredTrace = React.useMemo(() => {
    if (debugMode) return trace;
    // In non-debug mode, hide verbose tool calls and system instructions
    return trace.filter(step => {
      // Always show user input and final responses
      if (step.step_type === 'user_input' || step.step_type === 'final_response') return true;
      // Hide tool calls, but show tool_results that contain diagrams
      if (step.step_type === 'tool_call') return false;
      if (step.step_type === 'tool_result') {
        const content = String(step.metadata?.output || step.content || '');
        // Show if it contains mermaid diagram
        if (content.includes('ATTACK_PATH_DIAGRAM') || content.includes('```mermaid')) return true;
        return false;
      }
      // Hide system instructions and thoughts
      if (step.step_type === 'system_instruction' || step.step_type === 'llm_thought') return false;
      return true;
    });
  }, [trace, debugMode]);

  // Check if a tool_result contains a diagram
  const isDiagramResult = (step: TraceStep): boolean => {
    if (step.step_type !== 'tool_result') return false;
    const content = String(step.metadata?.output || step.content || '');
    return content.includes('ATTACK_PATH_DIAGRAM') || content.includes('```mermaid');
  };

  // Group consecutive tool_call + tool_result pairs (but keep diagram results as messages)
  const groupedTrace = React.useMemo(() => {
    const groups: Array<{ type: 'message' | 'tool_group' | 'diagram', items: TraceStep[] }> = [];
    let currentToolGroup: TraceStep[] = [];

    filteredTrace.forEach((step, idx) => {
      // Diagram results should be rendered as standalone messages
      if (isDiagramResult(step)) {
        if (currentToolGroup.length > 0) {
          groups.push({ type: 'tool_group', items: [...currentToolGroup] });
          currentToolGroup = [];
        }
        groups.push({ type: 'diagram', items: [step] });
      } else if (step.step_type === 'tool_call' || step.step_type === 'tool_result') {
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
  }, [filteredTrace]);

  if (trace.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-th-text-muted p-8">
        <div className="w-16 h-16 rounded-full border-2 border-th-border flex items-center justify-center mb-4">
          <BrainCircuit className="w-8 h-8 opacity-30" />
        </div>
        <p className="text-sm text-th-text-muted text-center">
          Ask Proxi to help with system tasks, desktop automation, or incident response.
        </p>
      </div>
    );
  }

  return (
    <div ref={containerRef} onScroll={handleScroll} className="h-full overflow-y-auto p-4 space-y-4">
      {groupedTrace.map((group, groupIdx) => {
        // Render diagram results with RenderContent
        if (group.type === 'diagram') {
          const step = group.items[0];
          const diagramContent = String(step.metadata?.output || step.content || '');
          return (
            <div key={groupIdx} className="flex justify-start">
              <div className="max-w-[95%] rounded-2xl px-4 py-3 bg-th-surface border border-th-border text-th-text rounded-bl-sm">
                <div className="flex items-center gap-2 mb-2 text-xs opacity-70">
                  <Terminal className="w-3 h-3" />
                  <span className="uppercase tracking-wider">diagram</span>
                </div>
                <RenderContent content={diagramContent} />
              </div>
            </div>
          );
        }

        if (group.type === 'tool_group') {
          // Render collapsed tool group
          const isExpanded = expandedTools.has(groupIdx);
          const toolCalls = group.items.filter(i => i.step_type === 'tool_call');
          const hasResults = group.items.some(i => i.step_type === 'tool_result');
          
          return (
            <div key={groupIdx} className="ml-4">
              <button
                onClick={() => toggleToolExpand(groupIdx)}
                className="flex items-center gap-2 text-xs text-th-text-muted hover:text-th-text-sec transition-colors w-full"
              >
                <div className={`flex items-center gap-1.5 px-2 py-1 rounded bg-th-surface border border-th-border ${hasResults ? 'border-green-900' : 'border-yellow-900'}`}>
                  {hasResults ? (
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                  ) : (
                    <Loader2 className="w-3 h-3 text-yellow-500 animate-spin" />
                  )}
                  <span className="text-th-text-sec">
                    {toolCalls.map(t => {
                      const name = t.content?.toString().split('(')[0] || 'tool';
                      // Convert snake_case to readable text
                      return name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase());
                    }).join(', ')}
                  </span>
                  {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </div>
              </button>
              
              {isExpanded && (
                <div className="mt-2 ml-2 space-y-2 border-l border-th-border pl-3">
                  {group.items.map((item, idx) => (
                    <div key={idx} className="text-xs">
                      {item.step_type === 'tool_call' ? (
                        <div className="text-yellow-500 font-mono">
                          <Wrench className="w-3 h-3 inline mr-1" />
                          {item.content}
                        </div>
                      ) : (
                        <div className="text-green-400 font-mono bg-black/30 p-2 rounded max-h-32 overflow-y-auto">
                          {(() => {
                            const output = item.metadata?.output ?? item.content;
                            return typeof output === 'string'
                              ? output.substring(0, 500)
                              : JSON.stringify(output).substring(0, 500);
                          })()}
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
        
        // Check if content is command output (shouldn't render as markdown)
        const isCommandOutput = (text: string): boolean => {
          if (!text) return false;
          // User commands start with !
          if (isUser && text.startsWith('!')) return true;
          // Terminal output patterns
          if (text.includes('SUCCESS:') || text.includes('ERROR:')) return true;
          if (text.includes('BLOCKED:')) return true;
          // Looks like terminal/code output
          if (text.startsWith('$') || text.startsWith('#') || text.startsWith('root@')) return true;
          return false;
        };
        const isResponse = step.step_type === 'final_response';
        const isVerification = step.step_type === 'verification';
        const isScreenshot = step.step_type === 'status_change' && step.metadata?.screenshot;
        const isSeparator = step.step_type === 'status_change' && step.metadata?.separator;

        // Handle separator between conversations
        if (isSeparator) {
          return (
            <div key={groupIdx} className="flex items-center justify-center py-4">
              <div className="flex-1 h-px bg-th-border" />
              <span className="px-4 text-xs text-th-text-muted uppercase tracking-wider">New Conversation</span>
              <div className="flex-1 h-px bg-th-border" />
            </div>
          );
        }

        // Handle agent switch notifications
        const isAgentSwitch = step.step_type === 'agent_switch' || 
          (step.step_type === 'status_change' && step.metadata?.agent);
        if (isAgentSwitch) {
          const agentName = step.metadata?.agent || 'Agent';
          const agentOS = step.metadata?.os || '';
          return (
            <div key={groupIdx} className="flex items-center justify-center py-2">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-900/30 border border-blue-800/50">
                <Monitor className="w-3.5 h-3.5 text-blue-400" />
                <span className="text-xs text-blue-300">
                  {step.content || `Connected to ${agentName} (${agentOS})`}
                </span>
              </div>
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
                  : 'bg-th-surface border border-th-border text-th-text rounded-bl-sm'
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
                {typeof step.content === 'string' ? (
                  // Check for evidence in content
                  (() => {
                    const evidenceParsed = parseEvidenceFromMessage(step.content);
                    if (evidenceParsed.hasEvidence && !isUser) {
                      return (
                        <div>
                          {evidenceParsed.remainingContent && (
                            <div className="mb-2">{evidenceParsed.remainingContent}</div>
                          )}
                          <EvidenceCard
                            evidenceId={evidenceParsed.evidenceId!}
                            claim={evidenceParsed.claim!}
                            evidenceType={step.metadata?.evidence_type}
                            data={step.metadata?.evidence_data}
                            imageUrl={step.metadata?.screenshot}
                            confidence={step.metadata?.confidence}
                            timestamp={step.metadata?.timestamp}
                            defaultExpanded={false}
                          />
                        </div>
                      );
                    }
                    return null;
                  })() ||
                  (isCommandOutput(step.content) || isUser ? (
                    // Plain text for commands and user input
                    <span className={isUser && step.content.startsWith('!') ? 'font-mono' : ''}>
                      {isThought ? filterPlanText(step.content) : step.content}
                    </span>
                  ) : (
                    // Markdown for AI responses
                    <ReactMarkdown
                      components={{
                        // Style markdown elements
                        p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                        strong: ({children}) => <strong className="font-semibold text-proxi-accent">{children}</strong>,
                        em: ({children}) => <em className="text-th-text">{children}</em>,
                        ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                        ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                        li: ({children}) => <li className="ml-2">{children}</li>,
                        code: ({children, className}) => {
                          const isBlock = className?.includes('language-');
                          // Render mermaid code blocks as interactive diagrams
                          if (className?.includes('language-mermaid')) {
                            const chartCode = String(children).replace(/\n$/, '');
                            return <MermaidDiagram chart={chartCode} />;
                          }
                          return isBlock ? (
                            <code className="block bg-th-code/50 p-2 rounded my-2 font-mono text-xs overflow-x-auto whitespace-pre-wrap">{children}</code>
                          ) : (
                            <code className="bg-th-code/30 px-1 rounded font-mono text-proxi-warning">{children}</code>
                          );
                        },
                        pre: ({children}) => {
                          // If the child is a MermaidDiagram (from our code handler), don't wrap in pre
                          const child = React.Children.toArray(children)[0] as React.ReactElement;
                          if (child?.type === MermaidDiagram) return <>{children}</>;
                          return <pre className="bg-th-code/50 p-2 rounded my-2 overflow-x-auto">{children}</pre>;
                        },
                        h1: ({children}) => <h1 className="text-lg font-bold text-th-accent mb-2">{children}</h1>,
                        h2: ({children}) => <h2 className="text-base font-bold text-th-accent mb-2">{children}</h2>,
                        h3: ({children}) => <h3 className="text-sm font-bold text-th-accent mb-1">{children}</h3>,
                        blockquote: ({children}) => <blockquote className="border-l-2 border-th-accent pl-3 italic text-th-text-sec">{children}</blockquote>,
                      }}
                    >
                      {isThought ? filterPlanText(step.content) : wrapUnfencedMermaid(step.content)}
                    </ReactMarkdown>
                  ))
                ) : (
                  JSON.stringify(step.content)
                )}
              </div>
            </div>
          </div>
        );
      })}

      {/* Processing indicator */}
      {isProcessing && (
        <div className="flex justify-start">
          <div className="bg-th-surface border border-th-border rounded-2xl rounded-bl-sm px-4 py-3">
            <div className="flex items-center gap-2 text-th-text-sec">
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
