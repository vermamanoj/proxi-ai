// AppV3.tsx - Sidebar Layout (ChatGPT/Gemini style)
// Access via /#/v3 route

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { 
  Send, Camera, X, Loader2, Volume2, VolumeX, LogOut, Plus, 
  Square, Mic, MicOff, ChevronDown, Menu, Settings, MessageSquare,
  Clock, ChevronRight, Zap, Scale, FlaskConical, ClipboardList, Info,
  Shield, CheckCircle2, Monitor, Terminal, Lock, Unlock, Smartphone
} from 'lucide-react';
import { useProxiBrain } from '../hooks/useProxiBrain';
import { useGeminiLive } from '../hooks/useGeminiLive';
import { useAuth } from '../hooks/useAuth';
import { LandingPage } from './LandingPage';
import { LoginPage } from './LoginPage';
import { useWorkstations } from '../hooks/useWorkstations';
import { ChatView } from './ChatView';
import { ApprovalModal, ApprovalModalRequest } from './ApprovalModal';
import { MissionPanelCollapsible, Goal } from './MissionPanelCollapsible';
import { getSessions, getSession, SessionSummary } from '../services/sessionService';
import { Complexity, TraceStep, MessageSource } from '../types';

// Mode configurations - icons only in header
const MODES: { value: Complexity; label: string; icon: React.ReactNode; color: string; description: string }[] = [
  { value: 'quick', label: 'Quick', icon: <Zap className="w-4 h-4" />, color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50', description: 'Fast, no verify' },
  { value: 'balanced', label: 'Auto', icon: <Scale className="w-4 h-4" />, color: 'text-blue-400 bg-blue-500/20 border-blue-500/50', description: 'Default mode' },
  { value: 'thorough', label: 'Deep', icon: <FlaskConical className="w-4 h-4" />, color: 'text-green-400 bg-green-500/20 border-green-500/50', description: 'Full verification' },
  { value: 'plan', label: 'Plan', icon: <ClipboardList className="w-4 h-4" />, color: 'text-purple-400 bg-purple-500/20 border-purple-500/50', description: 'Plan only, no execute' },
];

// OS icons for agent selector
const getOsIcon = (name: string, description?: string) => {
  const text = `${name} ${description || ''}`.toLowerCase();
  if (text.includes('windows')) return '🪟';
  if (text.includes('linux') || text.includes('ubuntu') || text.includes('docker')) return '🐧';
  if (text.includes('mac')) return '🍎';
  return '💻';
};

export const AppV3: React.FC = () => {
  const { isAuthenticated, isLoading: authLoading, user, login: authLogin, logout } = useAuth();
  const [authView, setAuthView] = useState<'landing' | 'login'>('landing');
  const [audioEnabled, setAudioEnabled] = useState(true);
  const { activeWorkstation, workstations, setActiveWorkstation, isLoading: workstationsLoading } = useWorkstations();
  
  // Mode state
  const [currentMode, setCurrentMode] = useState<Complexity>('balanced');
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showAbout, setShowAbout] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [debugMode, setDebugMode] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  
  // Agent selector dropdown
  const [showAgentDropdown, setShowAgentDropdown] = useState(false);
  
  // Approval modal state
  const [approvalRequest, setApprovalRequest] = useState<ApprovalModalRequest | null>(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);

  // Hooks
  const { 
    status: brainStatus, 
    logs: brainLogs,  // Needed for goal extraction from logs
    lastTrace,
    missionState,
    isSpeaking,
    sendCommand, 
    sendVisionCommand,
    setExecutionMode,
    stopExecution,
    clearSession: brainClearSession,
    confirmAction,
    cancelAction,
    pendingAction,
    setLastTrace,
    setSessionId,
  } = useProxiBrain(audioEnabled, activeWorkstation?.id || null);

  const {
    connected: liveConnected,
    connectionStatus,
    logs: liveLogs,
    chatLogs: liveChatLogs,
    micMuted,
    connect: liveConnect,
    disconnect: liveDisconnect,
    toggleMicMute,
    sendCommand: liveSendCommand,
    clearSession: liveClearSession,
    loadSession: liveLoadSession,
    markActiveGoalFailed,
  } = useGeminiLive(true, audioEnabled, currentMode);

  // Auto-connect voice on page load when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      liveConnect();
    }
  }, [isAuthenticated]); // eslint-disable-line react-hooks/exhaustive-deps

  // Convert liveChatLogs to trace format for display
  const liveTrace: TraceStep[] = useMemo(() => {
    return liveChatLogs.map(log => {
      const source = (log.source || '').toUpperCase();
      let step_type: TraceStep['step_type'] = 'final_response';
      if (source === MessageSource.USER) step_type = 'user_input';
      else if (source === MessageSource.SYSTEM) step_type = 'system_instruction';
      else if (source === MessageSource.AGENT) step_type = 'final_response';
      else if (log.text?.startsWith('[TOOL]')) step_type = 'tool_call';
      return { step_type, content: log.text || '', metadata: log.metadata };
    });
  }, [liveChatLogs]);

  // Combine voice trace with backend trace (vision commands, text commands)
  const displayTrace = useMemo(() => {
    // Always combine both traces - voice logs AND backend results (vision, text commands)
    // Backend lastTrace contains vision-action results which must always show
    const combined = [...liveTrace, ...lastTrace];
    
    // Deduplicate by content (keep first occurrence)
    const seen = new Set<string>();
    return combined.filter(t => {
      const key = typeof t.content === 'string' ? t.content : JSON.stringify(t.content);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [liveTrace, lastTrace]);

  // Input state
  const [input, setInput] = useState('');
  const [stagedImages, setStagedImages] = useState<{ file: File; preview: string }[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Status
  const isProcessing = brainStatus === 'processing' || brainStatus === 'speaking';
  const isActivelyProcessing = brainStatus === 'processing';

  // Update execution mode when currentMode changes
  useEffect(() => {
    setExecutionMode(currentMode);
  }, [currentMode, setExecutionMode]);

  // Load sessions on mount and when sidebar opens
  useEffect(() => {
    if (isAuthenticated) {
      loadSessions();
    }
  }, [isAuthenticated]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  // Listen for approval requests from backend
  useEffect(() => {
    if (pendingAction) {
      console.log('[AppV3] pendingAction received:', pendingAction);
      setApprovalRequest({
        id: pendingAction.data?.approval_id || 'approval-' + Date.now(),
        title: 'Action Approval Required',
        command: pendingAction.data?.command || pendingAction.description || 'Unknown action',
        riskLevel: pendingAction.data?.risk_level || pendingAction.data?.riskLevel || 'moderate',
        reason: pendingAction.data?.reason || 'This action requires your approval',
        timeoutSeconds: 30,
      });
      setShowApprovalModal(true);
    }
  }, [pendingAction]);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await getSessions(20);
      setSessions(data);
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
    setSessionsLoading(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isActivelyProcessing) return;
    
    if (stagedImages.length > 0) {
      const prompt = input.trim() || "Analyze this image and describe what you see.";
      sendVisionCommand(stagedImages[0].file, prompt);
      setStagedImages([]);
      setInput('');
      return;
    }
    
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
    const files = Array.from(e.target.files || []);
    const newImages = files.map(file => ({ file, preview: URL.createObjectURL(file) }));
    setStagedImages(prev => [...prev, ...newImages].slice(0, 4)); // Max 4 images
  };

  const removeImage = (index: number) => {
    setStagedImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleNewSession = () => {
    liveClearSession();
    brainClearSession();
    setSidebarOpen(false);
  };

  // Load a historic session into the chat view
  const handleLoadSession = async (session: SessionSummary) => {
    try {
      const fullSession = await getSession(session.id);
      if (!fullSession || !fullSession.messages) {
        console.warn('No messages in session:', session.id);
        return;
      }
      
      // Convert session messages to trace format
      const traceSteps: TraceStep[] = fullSession.messages.map((msg, idx) => {
        let stepType: TraceStep['step_type'] = 'llm_thought';
        if (msg.source === 'user') stepType = 'user_input';
        else if (msg.source === 'agent') stepType = 'final_response';
        else if (msg.source === 'tool') stepType = 'tool_result';
        
        return {
          step_type: stepType,
          content: msg.text,
          metadata: msg.metadata
        };
      });
      
      // Load session into the brain hook
      brainClearSession();
      setLastTrace(traceSteps);
      setSessionId(session.id);
      console.log('[Session] Loaded session:', session.id, traceSteps.length, 'messages');
      setSidebarOpen(false);
    } catch (e) {
      console.error('Failed to load session:', e);
    }
  };

  const handleApprove = () => {
    confirmAction?.();
    setShowApprovalModal(false);
    setApprovalRequest(null);
  };

  const handleDeny = () => {
    markActiveGoalFailed?.('User denied approval');
    cancelAction?.();
    setShowApprovalModal(false);
    setApprovalRequest(null);
  };

  // Auth loading state
  if (authLoading) {
    return (
      <div className="h-screen bg-black flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-proxi-accent mx-auto mb-4 animate-spin" />
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated - show landing or login
  if (!isAuthenticated) {
    if (authView === 'login') {
      return <LoginPage onLogin={authLogin} onBack={() => setAuthView('landing')} />;
    }
    return <LandingPage onLogin={() => setAuthView('login')} />;
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const currentModeConfig = MODES.find(m => m.value === currentMode) || MODES[1];

  // Extract mission goals - use missionState.goals from hook (already parsed there)
  const missionGoals: Goal[] = missionState?.goals?.length > 0 
    ? missionState.goals.map(g => ({
        id: g.id,
        title: g.title,
        description: g.description,
        status: g.status,
        result: g.result
      }))
    : (missionState?.active && missionState?.goal ? [{
        id: 'current-mission',
        title: missionState.goal,
        status: missionState.phase === 'success' ? 'complete' : 
                missionState.phase === 'failed' ? 'failed' : 
                missionState.phase === 'executing' ? 'active' : 'pending',
      }] : []);

  return (
    <div className="h-[100dvh] bg-proxi-black text-gray-200 flex font-mono overflow-hidden">
      
      {/* SIDEBAR OVERLAY (mobile) */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* LEFT SIDEBAR */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 bg-gray-900 border-r border-gray-800
        flex flex-col
        transform transition-transform duration-200
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Sidebar Header */}
        <div className="p-3 border-b border-gray-800">
          <button
            onClick={handleNewSession}
            className="w-full flex items-center gap-2 px-3 py-2.5 bg-proxi-accent/10 hover:bg-proxi-accent/20 text-proxi-accent rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm font-medium">New Chat</span>
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto">
          {sessionsLoading ? (
            <div className="flex items-center justify-center h-20">
              <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-4 text-center text-gray-600 text-sm">
              <MessageSquare className="w-6 h-6 mx-auto mb-2 opacity-50" />
              <p>No sessions yet</p>
            </div>
          ) : (
            <div className="py-2">
              <div className="px-3 py-1 text-xs text-gray-500 uppercase tracking-wider">Recent</div>
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => handleLoadSession(session)}
                  className="w-full px-3 py-2 text-left hover:bg-gray-800/50 transition-colors group"
                >
                  <p className="text-sm text-gray-300 truncate">{session.title || 'Untitled'}</p>
                  <div className="flex items-center gap-1 text-xs text-gray-600 mt-0.5">
                    <Clock className="w-3 h-3" />
                    <span>{formatDate(session.updated_at || session.created_at)}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-gray-800 space-y-1">
          <button 
            onClick={() => setDebugMode(!debugMode)}
            className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
              debugMode ? 'bg-yellow-500/20 text-yellow-400' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            }`}
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4" />
              <span>Debug Mode</span>
            </div>
            <div className={`w-8 h-4 rounded-full transition-colors ${debugMode ? 'bg-yellow-500' : 'bg-gray-600'}`}>
              <div className={`w-3 h-3 rounded-full bg-white mt-0.5 transition-transform ${debugMode ? 'translate-x-4 ml-0.5' : 'translate-x-0.5'}`} />
            </div>
          </button>
          <button 
            onClick={() => setShowAbout(true)}
            className="w-full flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg text-sm"
          >
            <Info className="w-4 h-4" />
            <span>About Proxi</span>
          </button>
          <button 
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 text-red-400 hover:text-red-300 hover:bg-gray-800 rounded-lg text-sm"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* HEADER */}
        <header className="flex items-center justify-between px-3 py-2 border-b border-gray-800 bg-gray-900/95 backdrop-blur shrink-0">
          {/* Left: Hamburger + Brand */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden p-1.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-yellow-500 animate-pulse' : liveConnected ? 'bg-green-500' : 'bg-gray-500'}`} />
              <h1 className="text-sm font-bold tracking-wider">
                PROXI<span className="text-proxi-accent">.OS</span>
              </h1>
            </div>
          </div>

          {/* Center: Agent Selector */}
          <div className="relative">
            <button
              onClick={() => setShowAgentDropdown(!showAgentDropdown)}
              className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl transition-colors"
              disabled={workstationsLoading}
            >
              <span className="text-base">{activeWorkstation ? getOsIcon(activeWorkstation.name, activeWorkstation.description) : '💻'}</span>
              <span className="text-sm text-gray-200 max-w-[100px] truncate">{activeWorkstation?.name || 'Select Agent'}</span>
              <div className={`w-2 h-2 rounded-full ${
                activeWorkstation?.status === 'online' ? 'bg-green-400' : 
                activeWorkstation?.status === 'offline' ? 'bg-red-400' : 'bg-gray-500'
              }`} />
            </button>
            
            {/* Agent Dropdown */}
            {showAgentDropdown && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowAgentDropdown(false)} />
                <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 min-w-[200px] py-1">
                  <div className="px-3 py-1.5 text-xs text-gray-500 uppercase">Agents</div>
                  {workstations.map((ws) => {
                    const isOffline = ws.status === 'offline' || ws.status === 'error';
                    const isActive = activeWorkstation?.id === ws.id;
                    return (
                      <button
                        key={ws.id}
                        onClick={() => { if (!isOffline) { setActiveWorkstation(ws.id); setShowAgentDropdown(false); }}}
                        disabled={isOffline}
                        className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors ${
                          isOffline ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-800'
                        } ${isActive ? 'bg-gray-800' : ''}`}
                      >
                        <span>{getOsIcon(ws.name, ws.description)}</span>
                        <div className={`w-2 h-2 rounded-full ${ws.status === 'online' ? 'bg-green-400' : 'bg-red-400'}`} />
                        <span className="flex-1 text-left truncate">{ws.name}</span>
                        {isActive && <span className="text-proxi-accent">✓</span>}
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </div>

          {/* Right: Audio Toggle only (mode moved to input row) */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => setAudioEnabled(!audioEnabled)}
              className={`p-1.5 rounded-lg transition-colors ${audioEnabled ? 'text-proxi-accent' : 'text-gray-500'}`}
              title={audioEnabled ? 'Mute audio' : 'Enable audio'}
            >
              {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Plan Mode Banner */}
        {currentMode === 'plan' && (
          <div className="px-3 py-2 bg-purple-500/10 border-b border-purple-500/30 text-purple-300 text-xs flex items-center gap-2">
            <ClipboardList className="w-4 h-4" />
            <span>Plan Mode: Agent will show steps without executing. Say "execute" to run.</span>
          </div>
        )}

        {/* Mission Panel (if active) */}
        {missionGoals.length > 0 && (
          <div className="px-3 py-2 border-b border-gray-800">
            <MissionPanelCollapsible goals={missionGoals} />
          </div>
        )}

        {/* CHAT AREA */}
        <div className="flex-1 overflow-hidden">
          <ChatView
            trace={displayTrace}
            isProcessing={isProcessing}
            debugMode={debugMode}
          />
        </div>

        {/* INPUT AREA */}
        <footer className="border-t border-gray-800 bg-gray-900/95 backdrop-blur p-3 shrink-0">
          
          {/* Image Preview Row (above input) */}
          {stagedImages.length > 0 && (
            <div className="flex gap-2 mb-2 pb-2 border-b border-gray-800 overflow-x-auto">
              {stagedImages.map((img, idx) => (
                <div key={idx} className="relative shrink-0">
                  <img src={img.preview} className="w-16 h-16 rounded-lg object-cover border border-gray-700" />
                  <button
                    onClick={() => removeImage(idx)}
                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center"
                  >
                    <X className="w-3 h-3 text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-2">
            {/* Text Input Row */}
            <div className="relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder="Ask Proxi..."
                rows={1}
                className="w-full px-4 py-3 pr-12 bg-gray-800 border border-gray-700 rounded-xl text-gray-200 placeholder-gray-500 resize-none focus:outline-none focus:border-proxi-accent transition-colors"
                style={{ minHeight: '48px', maxHeight: '150px' }}
              />
              {/* Camera button inside textarea */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-gray-300 transition-colors"
              >
                <Camera className="w-5 h-5" />
              </button>
            </div>

            {/* Controls Row: | mode ^ | mic | <space> | send | */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                {/* Mode Selector */}
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowModeDropdown(!showModeDropdown)}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl transition-colors"
                    title={`${currentModeConfig.label}: ${currentModeConfig.description}`}
                  >
                    <span className={currentModeConfig.color.split(' ')[0]}>{currentModeConfig.icon}</span>
                    <span className="text-sm text-gray-200">{currentModeConfig.label}</span>
                  </button>
                  
                  {/* Mode Dropdown (opens upward) */}
                  {showModeDropdown && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setShowModeDropdown(false)} />
                      <div className="absolute bottom-full mb-2 left-0 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 min-w-[180px] py-1">
                        <div className="px-3 py-1.5 text-xs text-gray-500 uppercase">Execution Mode</div>
                        {MODES.map((mode) => (
                          <button
                            key={mode.value}
                            type="button"
                            onClick={() => { setCurrentMode(mode.value); setShowModeDropdown(false); }}
                            className={`w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-gray-800 ${
                              currentMode === mode.value ? 'bg-gray-800' : ''
                            }`}
                          >
                            <span className={mode.color.split(' ')[0]}>{mode.icon}</span>
                            <div className="flex-1 text-left">
                              <div className="text-gray-200">{mode.label}</div>
                              <div className="text-xs text-gray-500">{mode.description}</div>
                            </div>
                            {currentMode === mode.value && <span className="text-proxi-accent">✓</span>}
                          </button>
                        ))}
                      </div>
                    </>
                  )}
                </div>

                {/* Mic Button */}
                <button
                  type="button"
                  onClick={toggleMicMute}
                  className={`p-2.5 rounded-xl transition-colors ${
                    !micMuted ? 'bg-proxi-accent text-black' : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}
                  title={micMuted ? 'Unmute microphone' : 'Mute microphone'}
                >
                  {micMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                </button>

                {/* Stop Button (TTS / Processing) */}
                {(isProcessing || isSpeaking) && (
                  <button
                    type="button"
                    onClick={stopExecution}
                    className="p-2.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-xl transition-colors"
                    title="Stop"
                  >
                    <Square className="w-5 h-5" />
                  </button>
                )}

                {/* Continue Button (stalled/failed recovery) */}
                {(missionState?.phase === 'stalled' || missionState?.phase === 'failed') && !isProcessing && (
                  <button
                    type="button"
                    onClick={() => sendCommand('Please continue where you left off')}
                    className="px-3 py-2 bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 rounded-xl text-sm hover:bg-yellow-500/30 transition-colors"
                  >
                    Continue
                  </button>
                )}
              </div>

              {/* Send Button */}
              {isActivelyProcessing ? (
                <div className="p-2.5 text-proxi-accent">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim() && stagedImages.length === 0}
                  className="p-2.5 bg-proxi-accent text-black rounded-xl disabled:opacity-50 disabled:cursor-not-allowed hover:bg-proxi-accent/90 transition-colors"
                >
                  <Send className="w-5 h-5" />
                </button>
              )}
            </div>
          </form>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={handleFileSelect}
            className="hidden"
            multiple
          />
        </footer>
      </main>

      {/* APPROVAL MODAL */}
      {approvalRequest && (
        <ApprovalModal
          request={approvalRequest}
          onApprove={handleApprove}
          onDeny={handleDeny}
          isOpen={showApprovalModal}
        />
      )}

      {/* ABOUT MODAL */}
      {showAbout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
          <div className="bg-gray-900 rounded-2xl border border-gray-800 w-full max-w-2xl max-h-[90vh] overflow-y-auto relative">
            <button
              onClick={() => setShowAbout(false)}
              className="absolute top-4 right-4 text-gray-500 hover:text-white z-10"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="p-6 sm:p-8 space-y-6">
              {/* Header */}
              <div className="text-center">
                <div className="inline-flex items-center gap-2 mb-3">
                  <Zap className="w-8 h-8 text-proxi-accent" />
                  <span className="text-2xl font-bold">PROXI</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold mb-2">From Advice to Action. Finally.</h2>
                <p className="text-gray-400">Your AI that executes real work on real computers — with proof and control.</p>
              </div>

              {/* Problem/Solution */}
              <div className="bg-gray-800/50 rounded-xl p-4 text-center">
                <p className="text-gray-300">AI can think. <span className="text-gray-500">Work still needs keyboards.</span></p>
                <p className="text-proxi-accent mt-2 font-medium">Proxi executes on real computers from your phone.</p>
              </div>

              {/* Trust by Design */}
              <div>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Trust by Design
                </h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle2 className="w-4 h-4 text-green-400" />
                      <span className="font-medium text-sm">Verified Execution</span>
                    </div>
                    <ul className="text-xs text-gray-400 space-y-1">
                      <li>• Screenshots as evidence</li>
                      <li>• Visual confirmation on mobile</li>
                      <li>• No "agent said it worked"</li>
                    </ul>
                  </div>
                  <div className="bg-black/30 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Shield className="w-4 h-4 text-blue-400" />
                      <span className="font-medium text-sm">Safety & Control</span>
                    </div>
                    <div className="text-xs space-y-1">
                      <div className="flex items-center gap-2"><span className="w-2 h-2 bg-green-500 rounded-full"></span><span className="text-gray-400">Safe — auto-allowed</span></div>
                      <div className="flex items-center gap-2"><span className="w-2 h-2 bg-yellow-500 rounded-full"></span><span className="text-gray-400">Sensitive — approval required</span></div>
                      <div className="flex items-center gap-2"><span className="w-2 h-2 bg-red-500 rounded-full"></span><span className="text-gray-400">Blocked — never executed</span></div>
                    </div>
                  </div>
                </div>
                <p className="text-center text-sm text-gray-400 italic mt-3">"Proxi never decides success. Reality does."</p>
              </div>

              {/* OS-Aware */}
              <div>
                <h3 className="text-lg font-semibold mb-3">OS-Aware Intelligence</h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-black/30 rounded-lg p-3 flex items-center gap-3">
                    <Unlock className="w-5 h-5 text-green-400" />
                    <div>
                      <p className="text-sm font-medium">Unlocked</p>
                      <p className="text-xs text-gray-500">Full UI control</p>
                    </div>
                  </div>
                  <div className="bg-black/30 rounded-lg p-3 flex items-center gap-3">
                    <Lock className="w-5 h-5 text-yellow-400" />
                    <div>
                      <p className="text-sm font-medium">Locked</p>
                      <p className="text-xs text-gray-500">Terminal fallback</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Inspiration */}
              <div className="text-center text-sm text-gray-400 border-t border-gray-800 pt-4">
                <p>Built for real moments — like negotiating pricing in a meeting without a laptop, knowing the data was on a computer back at the office.</p>
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between text-xs text-gray-600 border-t border-gray-800 pt-4">
                <span>Powered by Gemini 3</span>
                <span>Windows & Linux supported</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AppV3;
