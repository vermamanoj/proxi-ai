import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Settings, Mic, MicOff, Send, Camera, X, CheckCircle2, Loader2, Zap, BrainCircuit, Volume2, VolumeX, LogOut, Plus, History, MessageSquare, Monitor, ChevronDown, ChevronUp, Trash2, Info } from 'lucide-react';
import { useProxiBrain } from './hooks/useProxiBrain';
import { useGeminiLive } from './hooks/useGeminiLive';
import { useBackendHealth } from './hooks/useBackendHealth';
import { useAuth } from './hooks/useAuth';
import { ChatView } from './components/ChatView';
import { MissionProgress } from './components/MissionProgress';
import { ApprovalCard } from './components/ApprovalCard';
import { ApprovalModal, ApprovalModalRequest } from './components/ApprovalModal';
import { EscalationAlert, EscalationRequest } from './components/EscalationAlert';
import { LandingPage } from './components/LandingPage';
import { LoginPage } from './components/LoginPage';
import { VerificationBadge } from './components/VerificationBadge';
import { MissionPlan, Goal } from './components/MissionPlan';
import { SessionHistory } from './components/SessionHistory';
import { AgentSelector } from './components/AgentSelector';
import { ApprovalRequest, TraceStep, MessageSource } from './types';

const App: React.FC = () => {
  // Auth state
  const { isAuthenticated, isLoading: authLoading, user, login, logout, redeemMagicLink } = useAuth();
  const [authView, setAuthView] = useState<'landing' | 'login'>('landing');
  const [magicLinkStatus, setMagicLinkStatus] = useState<'checking' | 'invalid' | null>(null);

  // Handle magic link in URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const magicToken = params.get('magic');
    
    if (magicToken && !isAuthenticated && !authLoading) {
      setMagicLinkStatus('checking');
      redeemMagicLink(magicToken).then((success) => {
        if (success) {
          // Clear the magic token from URL
          window.history.replaceState({}, '', window.location.pathname);
          setMagicLinkStatus(null);
        } else {
          setMagicLinkStatus('invalid');
        }
      });
    }
  }, [isAuthenticated, authLoading, redeemMagicLink]);

  // Audio output toggle state
  const [audioEnabled, setAudioEnabled] = useState(true);
  // Mode: 'chat' = voice only, 'remote' = backend + agents
  const [mode, setMode] = useState<'chat' | 'remote'>('remote');
  const coreEnabled = mode === 'remote'; // Backward compat
  // Collapsible panels
  const [missionExpanded, setMissionExpanded] = useState(true);
  const [showDebugLogs, setShowDebugLogs] = useState(false);

  // Hook 1: Text & Vision (REST API)
  const { 
    status: brainStatus, 
    logs: brainLogs, 
    lastTrace,
    complexity,
    pendingAction,
    missionState,
    isSpeaking,
    sendCommand, 
    sendVisionCommand,
    toggleComplexity,
    confirmAction,
    cancelAction,
    logSystemError,
    clearSession: brainClearSession
  } = useProxiBrain(audioEnabled);

  // Hook 2: Real-time Voice (Live API / WebRTC)
  const { 
    connected: liveConnected,
    connectionStatus,
    connect: liveConnect, 
    disconnect: liveDisconnect, 
    sendCommand: liveSendCommand,
    volume: liveVolume, 
    logs: liveLogs, 
    activeTool: liveActiveTool,
    micMuted,
    toggleMicMute,
    clearSession: liveClearSession,
    loadSession: liveLoadSession
  } = useGeminiLive(coreEnabled, audioEnabled, complexity);

  // Hook 3: Backend Health Monitoring (only when core is enabled)
  const { status: backendStatus, mode: backendMode } = useBackendHealth(coreEnabled ? 5000 : 0);

  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showSessionHistory, setShowSessionHistory] = useState(false);
  const [animTick, setAnimTick] = useState(0);
  const [stagedImage, setStagedImage] = useState<{ file: File; preview: string } | null>(null);

  // Animation ticker for voice visualization - only animate when actually speaking
  const isLiveSpeaking = liveVolume > 0.02;
  useEffect(() => {
    if (liveConnected && !micMuted && isLiveSpeaking) {
      const interval = setInterval(() => setAnimTick(t => t + 1), 100);
      return () => clearInterval(interval);
    }
  }, [liveConnected, micMuted, isLiveSpeaking]);

  // Auto-connect voice on page load
  useEffect(() => {
    liveConnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Convert liveLogs to trace format for display when using voice
  const liveTrace: TraceStep[] = useMemo(() => {
    return liveLogs.map(log => ({
      step_type: (log.source === MessageSource.USER ? 'user_input' 
               : log.metadata?.screenshot ? 'status_change'  // Screenshots need status_change for proper rendering
               : log.metadata?.completed ? 'tool_result'  // Completed tools get tool_result type
               : log.source === MessageSource.AGENT ? 'final_response'
               : log.source === MessageSource.TOOL ? 'tool_call'
               : 'status_change') as TraceStep['step_type'],
      content: log.text,
      metadata: log.metadata
    }));
  }, [liveLogs]);

  // Use liveTrace when voice connected, otherwise use lastTrace
  const displayTrace: TraceStep[] = liveConnected ? liveTrace : lastTrace;
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Extract mission goals from logs
  const missionGoals: Goal[] = useMemo(() => {
    const goals: Goal[] = [];
    const goalUpdates: Record<string, { status: Goal['status']; result?: string }> = {};
    
    // First pass: collect all goal updates
    for (const log of liveLogs) {
      if (log.metadata?.goalUpdate) {
        const update = log.metadata.goalUpdate;
        goalUpdates[update.goal_id] = { status: update.status, result: update.result };
      }
    }
    
    // Second pass: find plan and apply updates
    for (const log of liveLogs) {
      if (log.metadata?.plan) {
        for (const g of log.metadata.plan) {
          const update = goalUpdates[g.id];
          goals.push({
            id: g.id,
            title: g.title,
            description: g.description,
            status: update?.status || g.status || 'pending',
            result: update?.result
          });
        }
        break; // Only use first plan found
      }
    }
    
    return goals;
  }, [liveLogs]);

  // Extract pending escalation from logs
  const pendingEscalation = useMemo(() => {
    for (let i = liveLogs.length - 1; i >= 0; i--) {
      const log = liveLogs[i];
      if (log.metadata?.escalation) {
        // Check if there's a subsequent user response
        const hasResponse = liveLogs.slice(i + 1).some(l => 
          l.source === MessageSource.USER
        );
        if (!hasResponse) {
          return {
            id: `esc-${i}`,
            message: log.metadata.reason,
            context: log.metadata.missionId,
            timestamp: log.timestamp
          };
        }
      }
    }
    return null;
  }, [liveLogs]);

  // Extract pending approval from logs (for command guard approvals)
  const pendingApproval = useMemo(() => {
    // Find the most recent approval_required log that hasn't been responded to
    for (let i = liveLogs.length - 1; i >= 0; i--) {
      const log = liveLogs[i];
      if (log.metadata?.approvalRequired) {
        // Check if there's a subsequent user response (yes/no)
        const hasResponse = liveLogs.slice(i + 1).some(l => 
          l.source === MessageSource.USER && (l.text.toLowerCase().includes('yes') || l.text.toLowerCase().includes('no'))
        );
        if (!hasResponse) {
          return {
            command: log.metadata.command,
            reason: log.metadata.reason,
            riskLevel: log.metadata.riskLevel || 'moderate'
          };
        }
      }
    }
    return null;
  }, [liveLogs]);

  // Convert pendingAction to ApprovalRequest format (for useProxiBrain approvals)
  const approvalRequest: ApprovalRequest | null = pendingAction ? {
    id: `apr-${Date.now()}`,
    type: 'binary',
    title: 'Authorization Required',
    description: pendingAction.description,
    metadata: pendingAction.data
  } : null;

  // Status - don't block input during speech, only during actual processing
  const isProcessing = brainStatus === 'processing' || !!liveActiveTool;
  const statusColor = isProcessing ? 'bg-yellow-500' : isSpeaking ? 'bg-blue-500' : liveConnected ? 'bg-green-500' : 'bg-gray-500';

  useEffect(() => {
    if (brainStatus === 'idle') {
      inputRef.current?.focus();
    }
  }, [brainStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isProcessing) return;
    
    // If we have a staged image, submit with vision-action
    if (stagedImage) {
      const prompt = input.trim() || "Analyze this image and describe what you see.";
      sendVisionCommand(stagedImage.file, prompt);
      clearStagedImage();
      setInput('');
      return;
    }
    
    // Normal text submission
    if (input.trim()) {
      if (liveConnected) {
        liveSendCommand(input);
      } else {
        sendCommand(input);
      }
      setInput('');
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Stage the image for preview, don't submit yet
      const preview = URL.createObjectURL(file);
      setStagedImage({ file, preview });
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const clearStagedImage = () => {
    if (stagedImage?.preview) URL.revokeObjectURL(stagedImage.preview);
    setStagedImage(null);
  };

  // Auth loading state or magic link checking
  if (authLoading || magicLinkStatus === 'checking') {
    return (
      <div className="h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <Zap className="w-12 h-12 text-proxi-accent mx-auto mb-4 animate-pulse" />
          <p className="text-gray-400">
            {magicLinkStatus === 'checking' ? 'Verifying access link...' : 'Loading...'}
          </p>
        </div>
      </div>
    );
  }

  // Not authenticated - show landing or login
  if (!isAuthenticated) {
    // Show invalid magic link error
    if (magicLinkStatus === 'invalid') {
      return (
        <div className="h-screen bg-black flex items-center justify-center">
          <div className="text-center max-w-md px-4">
            <X className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Invalid or Expired Link</h2>
            <p className="text-gray-400 mb-6">
              This access link is no longer valid. It may have expired or been used too many times.
            </p>
            <button
              onClick={() => {
                setMagicLinkStatus(null);
                window.history.replaceState({}, '', window.location.pathname);
              }}
              className="px-4 py-2 bg-proxi-accent text-black rounded font-medium hover:bg-proxi-accent/90"
            >
              Go to Login
            </button>
          </div>
        </div>
      );
    }
    if (authView === 'login') {
      return <LoginPage onLogin={login} onBack={() => setAuthView('landing')} />;
    }
    return <LandingPage onLogin={() => setAuthView('login')} />;
  }

  // Authenticated - show main app
  return (
    <div className="h-screen bg-proxi-black text-gray-200 flex flex-col font-mono overflow-hidden">
      {/* Centered container for desktop - full width on mobile, max-width on larger screens */}
      <div className="h-full flex flex-col w-full max-w-2xl mx-auto lg:border-x lg:border-gray-800">
      
      {/* Mobile Safe Area Spacer - accounts for notch/status bar */}
      <div className="h-10 sm:h-0 bg-gray-900 shrink-0" />
      
      {/* Minimal Header */}
      <header className="flex items-center justify-between px-2 sm:px-4 py-2 sm:py-3 border-b border-gray-800 bg-gray-900 shrink-0 z-20 min-h-[48px]">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className={`w-2.5 h-2.5 rounded-full ${statusColor} ${isProcessing ? 'animate-pulse' : ''}`} />
          <h1 className="text-base sm:text-lg font-bold tracking-wider">
            PROXI<span className="text-proxi-accent">.OS</span>
          </h1>
          {/* Mode Toggle: Chat ↔ Remote */}
          <div className="flex items-center bg-gray-800 rounded-lg p-0.5">
            <button
              onClick={() => {
                setMode('chat');
                if (liveConnected) {
                  liveDisconnect();
                  setTimeout(() => liveConnect(), 500);
                }
              }}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-all ${
                mode === 'chat'
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
              title="Chat mode - Voice assistant only"
            >
              <MessageSquare className="w-3 h-3" />
              <span className="hidden sm:inline">Chat</span>
            </button>
            <button
              onClick={() => {
                setMode('remote');
                if (liveConnected) {
                  liveDisconnect();
                  setTimeout(() => liveConnect(), 500);
                }
              }}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-all ${
                mode === 'remote'
                  ? backendStatus === 'connected'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
              title="Remote mode - Desktop control via agents"
            >
              <Monitor className="w-3 h-3" />
              <span className="hidden sm:inline">Remote</span>
              {mode === 'remote' && backendStatus !== 'connected' && (
                <span className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse" />
              )}
            </button>
          </div>
          
          {/* Triple Handshake Badge - show when mission is active */}
          {missionState.active && (
            <VerificationBadge
              phase={missionState.phase as any}
              goal={missionState.goal}
              verificationStatus={missionState.verification?.status as any}
            />
          )}
        </div>
        
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* Audio Toggle with speaking indicator */}
          <button
            onClick={() => {
              const newState = !audioEnabled;
              setAudioEnabled(newState);
              // Immediately cancel any ongoing speech when muting
              if (!newState) {
                window.speechSynthesis.cancel();
              }
            }}
            className={`p-2 rounded-lg transition-all relative ${
              audioEnabled 
                ? 'text-blue-400 hover:text-blue-300 hover:bg-blue-500/10' 
                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
            }`}
            title={audioEnabled ? 'Mute Audio' : 'Enable Audio'}
          >
            {audioEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
            {/* Speaking indicator - animated ring */}
            {isSpeaking && (
              <span className="absolute inset-0 rounded-lg border-2 border-blue-400 animate-ping opacity-75" />
            )}
          </button>

          {/* Agent Selector - only in Remote mode */}
          {mode === 'remote' && <AgentSelector />}

          {/* Session History Button */}
          <button
            onClick={() => setShowSessionHistory(true)}
            className="p-2 text-gray-500 hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-colors"
            title="Session History"
          >
            <History className="w-5 h-5" />
          </button>

          {/* New Session Button */}
          <button
            onClick={() => {
              liveClearSession();
              brainClearSession();
            }}
            className="p-2 text-gray-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
            title="New Session (clear chat)"
          >
            <Plus className="w-5 h-5" />
          </button>
          
          {/* Settings */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <Settings className="w-5 h-5" />
          </button>

          {/* Logout */}
          <button
            onClick={logout}
            className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
            title={`Logout ${user?.displayName || ''}`}
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Settings Drawer */}
      {showSettings && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm" onClick={() => setShowSettings(false)}>
          <div 
            className="absolute right-0 top-0 h-full w-72 bg-proxi-dark border-l border-gray-800 p-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-bold text-gray-400">SETTINGS</h2>
              <button onClick={() => setShowSettings(false)} className="text-gray-500 hover:text-gray-300">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            {/* Settings Options */}
            <div className="space-y-4">
              {/* Reasoning Mode */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Reasoning Mode</label>
                <button
                  onClick={toggleComplexity}
                  className={`mt-2 w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                    complexity === 'deep'
                      ? 'border-purple-500 bg-purple-500/10 text-purple-400'
                      : 'border-gray-700 bg-gray-800 text-gray-400'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {complexity === 'deep' ? <BrainCircuit className="w-4 h-4" /> : <Zap className="w-4 h-4" />}
                    {complexity === 'deep' ? 'Deep Thought' : 'Fast Reflex'}
                  </span>
                  <span className="text-xs opacity-50">{complexity === 'deep' ? 'Pro' : 'Flash'}</span>
                </button>
              </div>
              
              {/* Debug Logs Toggle */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Debug Mode</label>
                <button
                  onClick={() => setShowDebugLogs(!showDebugLogs)}
                  className={`mt-2 w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                    showDebugLogs
                      ? 'border-orange-500 bg-orange-500/10 text-orange-400'
                      : 'border-gray-700 bg-gray-800 text-gray-400'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <Info className="w-4 h-4" />
                    {showDebugLogs ? 'Debug Logs ON' : 'Debug Logs OFF'}
                  </span>
                </button>
              </div>

              {/* Clear Chat History */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Actions</label>
                <button
                  onClick={() => {
                    liveClearSession();
                    brainClearSession();
                    setShowSettings(false);
                  }}
                  className="mt-2 w-full flex items-center justify-between p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all"
                >
                  <span className="flex items-center gap-2">
                    <Trash2 className="w-4 h-4" />
                    Clear Chat History
                  </span>
                </button>
              </div>

              {/* Current Mode Info */}
              <div className="pt-4 border-t border-gray-700">
                <div className="text-xs text-gray-500 mb-2">Current Mode</div>
                <div className={`p-3 rounded-lg border ${
                  mode === 'chat' 
                    ? 'border-blue-500/30 bg-blue-500/10' 
                    : 'border-green-500/30 bg-green-500/10'
                }`}>
                  <div className={`text-sm font-semibold ${mode === 'chat' ? 'text-blue-400' : 'text-green-400'}`}>
                    {mode === 'chat' ? '💬 Chat Mode' : '🖥️ Remote Control'}
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {mode === 'chat' 
                      ? 'Voice assistant only. No desktop access.' 
                      : 'Full desktop control via connected agents.'}
                  </div>
                </div>
              </div>

              {/* Mission Status - only in Remote mode */}
              {mode === 'remote' && missionState && missionState.active && (
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider">Current Mission</label>
                  <div className="mt-2 p-3 rounded-lg border border-gray-700 bg-gray-800/50">
                    <div className="text-xs text-gray-400">{missionState.goal || 'No active mission'}</div>
                    <div className={`mt-1 text-xs ${
                      missionState.verification?.status === 'success' ? 'text-green-400' :
                      missionState.verification?.status === 'failed' ? 'text-red-400' : 'text-yellow-400'
                    }`}>
                      {missionState.phase.toUpperCase()}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Chat Mode Banner */}
      {mode === 'chat' && (
        <div className="bg-blue-500/10 border-b border-blue-500/20 px-4 py-2 text-center">
          <p className="text-xs text-blue-400">
            💬 Chat Mode — Voice assistant only. Switch to <span className="font-semibold">Remote</span> for desktop control.
          </p>
        </div>
      )}

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* Collapsible Mission Panel - only in Remote mode when goals exist */}
        {mode === 'remote' && missionGoals.length > 0 && (
          <div className="shrink-0 border-b border-gray-800">
            <button
              onClick={() => setMissionExpanded(!missionExpanded)}
              className="w-full flex items-center justify-between px-4 py-2 bg-gray-900/50 hover:bg-gray-800/50 transition-colors"
            >
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                📋 Mission ({missionGoals.filter(g => g.status === 'complete').length}/{missionGoals.length})
              </span>
              {missionExpanded ? <ChevronUp className="w-4 h-4 text-gray-500" /> : <ChevronDown className="w-4 h-4 text-gray-500" />}
            </button>
            {missionExpanded && (
              <div className="px-3 pb-2">
                <MissionPlan goals={missionGoals} />
              </div>
            )}
          </div>
        )}
        
        {/* Chat View - always full, no tabs */}
        <ChatView trace={displayTrace} isProcessing={isProcessing} />
      </main>

      {/* Approval Card Overlay (for useProxiBrain) */}
      {approvalRequest && (
        <div className="absolute bottom-20 left-4 right-4 z-30">
          <ApprovalCard
            request={approvalRequest}
            onApprove={() => confirmAction()}
            onDeny={() => cancelAction()}
            isListening={liveConnected && !micMuted}
          />
        </div>
      )}

      {/* Escalation Alert (when agent needs human help) */}
      {pendingEscalation && (
        <div className="absolute top-20 left-4 right-4 z-40 max-w-md mx-auto">
          <EscalationAlert
            request={pendingEscalation as EscalationRequest}
            onRespond={(response) => {
              if (liveConnected) {
                liveSendCommand(response);
              } else {
                sendCommand(response);
              }
            }}
            onDismiss={() => {
              // User dismissed without responding - send a generic acknowledgment
              if (liveConnected) {
                liveSendCommand('Acknowledged, continue with best judgment');
              } else {
                sendCommand('Acknowledged, continue with best judgment');
              }
            }}
          />
        </div>
      )}

      {/* Command Guard Approval Modal (for useGeminiLive) */}
      {pendingApproval && (
        <ApprovalModal
          request={{
            id: `cmd-${Date.now()}`,
            title: 'Command Approval Required',
            command: pendingApproval.command,
            riskLevel: pendingApproval.riskLevel as any,
            reason: pendingApproval.reason,
            timeoutSeconds: 30
          }}
          isOpen={!!pendingApproval}
          onApprove={() => {
            if (liveConnected) {
              liveSendCommand('yes');
            } else {
              sendCommand('yes');
            }
          }}
          onDeny={() => {
            if (liveConnected) {
              liveSendCommand('no');
            } else {
              sendCommand('no');
            }
          }}
        />
      )}

      {/* Input Area - ChatGPT style: mic+voice when empty, mic+send when typing */}
      <footer className="border-t border-gray-800 bg-proxi-dark p-3 pb-safe">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          {/* File Upload */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            className="hidden"
            accept="image/*"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={`p-3 rounded-xl transition-colors ${
              stagedImage ? 'text-proxi-accent bg-proxi-accent/10' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
            }`}
          >
            <Camera className="w-5 h-5" />
          </button>

          {/* Staged Image Preview */}
          {stagedImage && (
            <div className="relative">
              <img 
                src={stagedImage.preview} 
                alt="Staged" 
                className="w-10 h-10 rounded-lg object-cover border border-proxi-accent"
              />
              <button
                type="button"
                onClick={clearStagedImage}
                className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center"
              >
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          )}

          {/* Text Input */}
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isProcessing ? "Processing..." : stagedImage ? "What should I do with this image?" : "Ask Proxi anything..."}
              disabled={isProcessing}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-proxi-accent/50 disabled:opacity-50"
            />
            {isProcessing && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="w-4 h-4 text-proxi-accent animate-spin" />
              </div>
            )}
          </div>

          {/* Right side buttons - changes based on input state */}
          <div className="flex items-center gap-1">
            {/* Mic button - always visible */}
            <button
              type="button"
              onClick={toggleMicMute}
              className={`p-3 rounded-xl transition-all ${
                !liveConnected
                  ? 'bg-gray-800 text-gray-500'
                  : micMuted
                  ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                  : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
              }`}
              title={!liveConnected ? 'Voice not connected' : micMuted ? 'Unmute Mic' : 'Mute Mic'}
              disabled={!liveConnected}
            >
              {micMuted || !liveConnected ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>

            {/* Show Voice Uplink OR Send based on input */}
            {input.trim() || stagedImage ? (
              /* Send Button - when there's text */
              <button
                type="submit"
                disabled={isProcessing}
                className="p-3 bg-proxi-accent text-black rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:bg-proxi-accent/80"
              >
                <Send className="w-5 h-5" />
              </button>
            ) : (
              /* Voice Uplink Button - when no text */
              <button
                type="button"
                onClick={liveConnected ? liveDisconnect : liveConnect}
                className={`p-3 rounded-xl transition-all ${
                  connectionStatus === 'listening'
                    ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                    : connectionStatus === 'connecting' || connectionStatus === 'connected'
                    ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/50'
                    : connectionStatus === 'error'
                    ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                    : 'bg-gray-800 text-gray-400 hover:text-gray-300'
                }`}
                title={liveConnected ? 'Disconnect Voice' : 'Connect Voice'}
              >
                {/* Animated bars when listening */}
                {connectionStatus === 'listening' && !micMuted ? (
                  <div className="flex items-end justify-center gap-0.5 w-5 h-5">
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="w-1 bg-green-400 rounded-full transition-all duration-100"
                        style={{
                          height: isLiveSpeaking 
                            ? `${Math.max(6, Math.min(20, 8 + liveVolume * 300 + Math.sin(animTick * 0.5 + i * 1.5) * 6))}px`
                            : `${[8, 12, 10, 6][i]}px`
                        }}
                      />
                    ))}
                  </div>
                ) : connectionStatus === 'connecting' ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <div className="flex items-end justify-center gap-0.5 w-5 h-5">
                    {[0, 1, 2, 3].map((i) => (
                      <div key={i} className="w-1 bg-current rounded-full" style={{ height: `${[8, 14, 10, 6][i]}px` }} />
                    ))}
                  </div>
                )}
              </button>
            )}
          </div>
        </form>
      </footer>
      </div>{/* End centered container */}

      {/* Session History Panel */}
      <SessionHistory
        isOpen={showSessionHistory}
        onClose={() => setShowSessionHistory(false)}
        onSelectSession={async (sessionId) => {
          try {
            const session = await import('./services/sessionService').then(m => m.getSession(sessionId));
            if (session?.messages && session.messages.length > 0) {
              liveLoadSession(session.messages);
            }
          } catch (e) {
            console.error('Failed to load session:', e);
          }
          setShowSessionHistory(false);
        }}
      />
    </div>
  );
};

export default App;
