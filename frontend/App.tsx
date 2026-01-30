// App.tsx

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Settings, Mic, MicOff, Send, Camera, X, CheckCircle2, Loader2, Zap, BrainCircuit, Volume2, VolumeX, LogOut, Plus, History, MessageSquare, Monitor, ChevronDown, ChevronUp, Trash2, Info, Link2, Menu, Square } from 'lucide-react';
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
import { MissionPanelCollapsible } from './components/MissionPanelCollapsible';
import { SessionHistory } from './components/SessionHistory';
import { AgentSelector } from './components/AgentSelector';
import { AdminPanel } from './components/AdminPanel';
import { MobileMenu } from './components/MobileMenu';
import { ApprovalRequest, TraceStep, MessageSource } from './types';
import { useWorkstations } from './hooks/useWorkstations';

const App: React.FC = () => {
  // Auth state
  const { isAuthenticated, isLoading: authLoading, user, login: authLogin, logout, redeemMagicLink } = useAuth();
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
  
  // Agent/workstation management - single source of truth
  const { activeWorkstation, workstations, setActiveWorkstation, isLoading: workstationsLoading, refreshWorkstations } = useWorkstations();

  // Wrapper login that refreshes workstations immediately after successful auth
  const login = async (username: string, password: string, rememberMe: boolean = false): Promise<boolean> => {
    const success = await authLogin(username, password, rememberMe);
    if (success) {
      // Immediately fetch workstations after login so user sees agents right away
      console.log('[App] Login successful, refreshing workstations...');
      refreshWorkstations();
    }
    return success;
  };

  // Collapsible panels
  const [missionExpanded, setMissionExpanded] = useState(true);
  const [showDebugLogs, setShowDebugLogs] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);

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
    setExecutionMode,
    confirmAction,
    cancelAction,
    logSystemError,
    clearSession: brainClearSession,
    stopExecution
  } = useProxiBrain(audioEnabled, activeWorkstation?.id || null);

  // Hook 2: Real-time Voice (Live API / WebRTC)
  const { 
    connected: liveConnected,
    connectionStatus,
    connect: liveConnect, 
    disconnect: liveDisconnect, 
    sendCommand: liveSendCommand,
    volume: liveVolume, 
    logs: liveLogs,  // Full logs for mission panel extraction
    chatLogs: liveChatLogs,  // Filtered logs for chat display
    activeTool: liveActiveTool,
    micMuted,
    toggleMicMute,
    clearSession: liveClearSession,
    loadSession: liveLoadSession,
    markActiveGoalFailed
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

  // Auto-connect voice on page load (desktop only - mobile doesn't support voice)
  useEffect(() => {
    const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
    if (!isCapacitor) {
      liveConnect();
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Convert liveChatLogs to trace format for display when using voice
  const liveTrace: TraceStep[] = useMemo(() => {
    return liveChatLogs.map(log => {
      // Determine step type based on log content and source
      let step_type: TraceStep['step_type'] = 'llm_thought';
      let content = log.text;
      
      if (log.source === MessageSource.USER) {
        step_type = 'user_input';
      } else if (log.metadata?.screenshot) {
        step_type = 'status_change';
      } else if (log.metadata?.completed) {
        step_type = 'tool_result';
      } else if (log.source === MessageSource.SYSTEM) {
        step_type = 'status_change';
      } else if (log.source === MessageSource.AGENT) {
        // Distinguish thinking from final responses
        if (log.text.startsWith('(Thinking)')) {
          step_type = 'llm_thought';
          content = log.text.replace('(Thinking) ', ''); // Clean up prefix
        } else if (log.text.startsWith('Core Result:')) {
          step_type = 'final_response';
          content = log.text.replace('Core Result: ', ''); // Clean up prefix
        } else {
          // Default agent messages are final responses
          step_type = 'final_response';
        }
      }
      
      return { step_type, content, metadata: log.metadata };
    });
  }, [liveChatLogs]);

  // Combine both traces - liveTrace for voice, lastTrace for text/direct commands
  // This ensures direct commands (!ls) show even when voice is connected
  const rawTrace: TraceStep[] = useMemo(() => {
    // If voice connected, combine both traces (voice + text commands)
    if (liveConnected) {
      // Avoid duplicates by using lastTrace only if it has newer content
      return [...liveTrace, ...lastTrace];
    }
    return [...liveTrace, ...lastTrace];
  }, [liveConnected, liveTrace, lastTrace]);
  
  // Filter trace based on debug mode - hide thinking when debug is OFF
  const displayTrace: TraceStep[] = useMemo(() => {
    if (showDebugLogs) {
      return rawTrace; // Show everything including thinking
    }
    // Hide verbose messages when debug is OFF
    const filtered = rawTrace.filter(step => {
      // Always show user input and final responses
      if (step.step_type === 'user_input') return true;
      if (step.step_type === 'final_response') return true;
      if (step.step_type === 'verification') return true;
      if (step.step_type === 'agent_switch') return true;  // Always show agent switches
      
      // Hide llm_thought in non-debug mode
      if (step.step_type === 'llm_thought') return false;
      
      // Hide delegation-related verbose messages
      const content = typeof step.content === 'string' ? step.content : '';
      if (content.includes('Handing off to Core')) return false;
      if (content.includes('delegate_task')) return false;
      if (content.includes('Analyzing the Request') || content.includes('Analyzing the request')) return false;
      if (content.includes('I\'ve determined') && content.includes('tool')) return false;
      
      return true;
    });
    
    // Fallback: if nothing passes filter, show raw trace (prevents blank screen)
    return filtered.length > 0 ? filtered : rawTrace;
  }, [rawTrace, showDebugLogs]);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Extract mission goals from logs (combine both voice and text logs)
  const missionGoals: Goal[] = useMemo(() => {
    const goalUpdates: Record<string, { status: Goal['status']; result?: string }> = {};
    let latestPlan: any[] | null = null;
    
    // Combine both log sources
    const allLogs = [...brainLogs, ...liveLogs];
    
    // Collect all goal updates and find the LATEST plan (not first)
    for (const log of allLogs) {
      if (log.metadata?.goalUpdate) {
        const update = log.metadata.goalUpdate;
        // Ensure goal_id is always a string for consistent matching
        goalUpdates[String(update.goal_id)] = { status: update.status, result: update.result };
      }
      if (log.metadata?.plan) {
        latestPlan = log.metadata.plan; // Keep updating to get the latest
      }
    }
    
    // Build goals from latest plan with updates applied
    if (!latestPlan) return [];
    
    return latestPlan.map(g => {
      // Ensure string comparison for goal IDs
      const update = goalUpdates[String(g.id)];
      return {
        id: g.id,
        title: g.title,
        description: g.description,
        status: update?.status || g.status || 'pending',
        result: update?.result
      };
    });
  }, [brainLogs, liveLogs]);

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

  // Status - show Stop button during processing, speaking, or live tool execution
  const isProcessing = brainStatus === 'processing' || brainStatus === 'speaking' || !!liveActiveTool;
  const isActivelyProcessing = brainStatus === 'processing' || !!liveActiveTool; // For input disabling
  const statusColor = isActivelyProcessing ? 'bg-yellow-500' : isSpeaking ? 'bg-blue-500' : liveConnected ? 'bg-green-500' : 'bg-gray-500';

  useEffect(() => {
    if (brainStatus === 'idle') {
      inputRef.current?.focus();
    }
  }, [brainStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isActivelyProcessing) return;
    
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
      // On mobile, hide back button (no landing page for app)
      const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
      return <LoginPage onLogin={login} onBack={isCapacitor ? undefined : () => setAuthView('landing')} />;
    }
    // Skip landing page on mobile - go straight to login
    const isCapacitor = typeof (window as any)?.Capacitor !== 'undefined';
    if (isCapacitor) {
      return <LoginPage onLogin={login} onBack={undefined} />;
    }
    return <LandingPage onLogin={() => setAuthView('login')} />;
  }

  // Authenticated - show main app
  return (
    <div className="h-[100dvh] bg-proxi-black text-gray-200 flex flex-col font-mono overflow-hidden">
      {/* Centered container for desktop - full width on mobile, max-width on larger screens */}
      <div className="h-full flex flex-col w-full max-w-2xl mx-auto lg:border-x lg:border-gray-800 overflow-hidden">
      
      {/* Mobile Safe Area Spacer - minimal, let CSS env() handle notch */}
      <div className="h-0 sm:h-0 shrink-0" style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }} />
      
      {/* Minimal Header - Mobile optimized */}
      <header className="flex items-center justify-between px-3 py-2 border-b border-gray-800 bg-gray-900 shrink-0 z-20">
        {/* Left: Title + Status */}
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${statusColor} ${isProcessing ? 'animate-pulse' : ''}`} />
          <h1 className="text-sm font-bold tracking-wider">
            PROXI<span className="text-proxi-accent">.OS</span>
          </h1>
        </div>

        {/* Center: Agent Selector */}
        <div className="flex items-center gap-2">
          <Monitor className="w-4 h-4 text-gray-500" />
          <AgentSelector 
            workstations={workstations}
            activeWorkstation={activeWorkstation}
            setActiveWorkstation={setActiveWorkstation}
            isLoading={workstationsLoading}
          />
        </div>

        {/* Right: New Session + Menu */}
        <div className="flex items-center gap-1">
          {/* New Session - always visible */}
          <button 
            onClick={() => { liveClearSession(); brainClearSession(); }} 
            className="p-2 text-gray-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors" 
            title="New Session"
          >
            <Plus className="w-5 h-5" />
          </button>
          
          {/* Desktop only buttons */}
          <div className="hidden sm:flex items-center gap-1">
            <button
              onClick={() => {
                const newState = !audioEnabled;
                setAudioEnabled(newState);
                if (!newState && window.speechSynthesis) window.speechSynthesis.cancel();
              }}
              className={`p-2 rounded-lg transition-all relative ${
                audioEnabled ? 'text-blue-400 hover:bg-blue-500/10' : 'text-gray-500 hover:bg-gray-800'
              }`}
              title={audioEnabled ? 'Mute Audio' : 'Enable Audio'}
            >
              {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
              {isSpeaking && <span className="absolute inset-0 rounded-lg border-2 border-blue-400 animate-ping opacity-75" />}
            </button>
            <button onClick={() => setShowSessionHistory(true)} className="p-2 text-gray-500 hover:text-purple-400 rounded-lg" title="History">
              <History className="w-4 h-4" />
            </button>
            <button onClick={() => setShowSettings(!showSettings)} className="p-2 text-gray-500 hover:text-gray-300 rounded-lg">
              <Settings className="w-4 h-4" />
            </button>
            <button onClick={logout} className="p-2 text-gray-500 hover:text-red-400 rounded-lg" title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          
          {/* Mobile: Hamburger Menu */}
          <button
            onClick={() => setShowMobileMenu(true)}
            className="sm:hidden p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800"
          >
            <Menu className="w-5 h-5" />
          </button>
        </div>
      </header>


      {/* Mobile Menu */}
      <MobileMenu
        isOpen={showMobileMenu}
        onClose={() => setShowMobileMenu(false)}
        audioEnabled={audioEnabled}
        onToggleAudio={() => {
          const newState = !audioEnabled;
          setAudioEnabled(newState);
          if (!newState && window.speechSynthesis) window.speechSynthesis.cancel();
        }}
        onShowHistory={() => setShowSessionHistory(true)}
        onShowSettings={() => setShowSettings(true)}
        onLogout={logout}
        onShowAdmin={() => setShowAdminPanel(true)}
        isAdmin={user?.role === 'admin'}
        userName={user?.displayName}
      />

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
              {/* Execution Mode */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Execution Mode</label>
                <select
                  value={complexity}
                  onChange={(e) => setExecutionMode(e.target.value as any)}
                  className="mt-2 w-full p-3 rounded-lg border border-gray-700 bg-gray-800 text-gray-300 text-sm focus:outline-none focus:border-proxi-accent"
                >
                  <option value="quick">⚡ Quick - Simple queries (Flash, no verify)</option>
                  <option value="balanced">⚖️ Balanced - Default mode (Flash, auto verify)</option>
                  <option value="thorough">🔬 Thorough - Critical ops (Pro, full verify)</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  {complexity === 'quick' && 'Fast execution, skips verification'}
                  {complexity === 'balanced' && 'Verifies action tasks automatically'}
                  {complexity === 'thorough' && 'Deep analysis with full verification'}
                </p>
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

              {/* Admin Panel - Only for admins */}
              {user?.role === 'admin' && (
                <div>
                  <label className="text-xs text-gray-500 uppercase tracking-wider">Admin</label>
                  <button
                    onClick={() => {
                      setShowAdminPanel(true);
                      setShowSettings(false);
                    }}
                    className="mt-2 w-full flex items-center justify-between p-3 rounded-lg border border-proxi-accent/30 bg-proxi-accent/10 text-proxi-accent hover:bg-proxi-accent/20 transition-all"
                  >
                    <span className="flex items-center gap-2">
                      <Link2 className="w-4 h-4" />
                      Magic Links
                    </span>
                    <span className="text-xs opacity-50">Manage</span>
                  </button>
                </div>
              )}

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

              {/* Mission Status */}
              {missionState && missionState.active && (
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

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* Collapsible Mission Panel - when goals exist */}
        {missionGoals.length > 0 && (
          <div className="shrink-0 mx-2 mt-2">
            <MissionPanelCollapsible goals={missionGoals} />
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
            onDeny={() => {
              markActiveGoalFailed('User denied approval');
              cancelAction();
            }}
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
            // Mark the active goal as failed/cancelled
            markActiveGoalFailed('User denied approval');
            if (liveConnected) {
              liveSendCommand('no');
            } else {
              sendCommand('no');
            }
          }}
        />
      )}

      {/* Input Area - ChatGPT style: mic+voice when empty, mic+send when typing */}
      <footer className="border-t border-gray-800 bg-proxi-dark p-3 shrink-0" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          {/* Camera/Image Upload - capture="environment" enables camera on mobile */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileSelect}
            className="hidden"
            accept="image/*"
            capture="environment"
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
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder={isActivelyProcessing ? "Processing..." : stagedImage ? "What should I do with this image?" : "Ask Proxi anything..."}
              disabled={isActivelyProcessing}
              rows={1}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-proxi-accent/50 disabled:opacity-50 resize-none overflow-hidden"
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
            {isProcessing && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="w-4 h-4 text-proxi-accent animate-spin" />
              </div>
            )}
          </div>

          {/* Continue button when stalled or failed */}
          {(missionState.phase === 'stalled' || missionState.phase === 'failed') && !isProcessing && (
            <button
              type="button"
              onClick={() => sendCommand('Please continue where you left off')}
              className="px-4 py-2 bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 rounded-xl text-sm hover:bg-yellow-500/30 transition-all"
            >
              Continue
            </button>
          )}

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

            {/* Show Stop, Send, or Voice based on state */}
            {isProcessing ? (
              /* Stop Button - when processing */
              <button
                type="button"
                onClick={stopExecution}
                className="p-3 bg-red-500 text-white rounded-xl transition-all hover:bg-red-600 animate-pulse"
                title="Stop execution"
              >
                <Square className="w-5 h-5 fill-current" />
              </button>
            ) : input.trim() || stagedImage ? (
              /* Send Button - when there's text */
              <button
                type="submit"
                disabled={isActivelyProcessing}
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

      {/* Admin Panel */}
      {showAdminPanel && (
        <AdminPanel onClose={() => setShowAdminPanel(false)} />
      )}

      {/* Floating New Session button - always accessible safety net */}
      {displayTrace.length > 3 && (
        <button
          onClick={() => { liveClearSession(); brainClearSession(); }}
          className="fixed bottom-24 right-4 z-50 p-3 bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-green-400 rounded-full shadow-lg border border-gray-700 transition-all"
          title="Start New Session"
        >
          <Plus className="w-5 h-5" />
        </button>
      )}
    </div>
  );
};

export default App;
