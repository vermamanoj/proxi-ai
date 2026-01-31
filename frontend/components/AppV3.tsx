// AppV3.tsx - Sidebar Layout (ChatGPT/Gemini style)
// Access via /#/v3 route

import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Camera, X, Loader2, Volume2, VolumeX, LogOut, Plus, 
  Square, Mic, MicOff, ChevronDown, Menu, Settings, MessageSquare,
  Clock, ChevronRight, Zap, Scale, FlaskConical, ClipboardList
} from 'lucide-react';
import { useProxiBrain } from '../hooks/useProxiBrain';
import { useGeminiLive } from '../hooks/useGeminiLive';
import { useAuth } from '../hooks/useAuth';
import { useWorkstations } from '../hooks/useWorkstations';
import { ChatView } from './ChatView';
import { ApprovalModal, ApprovalModalRequest } from './ApprovalModal';
import { MissionPanelCollapsible, Goal } from './MissionPanelCollapsible';
import { getSessions, SessionSummary } from '../services/sessionService';
import { Complexity } from '../types';

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
  const { logout, user } = useAuth();
  const [audioEnabled, setAudioEnabled] = useState(true);
  const { activeWorkstation, workstations, setActiveWorkstation, isLoading: workstationsLoading } = useWorkstations();
  
  // Mode state
  const [currentMode, setCurrentMode] = useState<Complexity>('balanced');
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  
  // Sidebar state
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  
  // Agent selector dropdown
  const [showAgentDropdown, setShowAgentDropdown] = useState(false);
  
  // Approval modal state
  const [approvalRequest, setApprovalRequest] = useState<ApprovalModalRequest | null>(null);
  const [showApprovalModal, setShowApprovalModal] = useState(false);

  // Hooks
  const { 
    status: brainStatus, 
    logs: brainLogs, 
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
  } = useProxiBrain(audioEnabled, activeWorkstation?.id || null);

  const {
    connected: liveConnected,
    connectionStatus,
    logs: liveLogs,
    micMuted,
    connect: liveConnect,
    disconnect: liveDisconnect,
    toggleMicMute,
    sendCommand: liveSendCommand,
    clearSession: liveClearSession,
  } = useGeminiLive(true, audioEnabled, currentMode);

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

  // Load sessions when sidebar opens
  useEffect(() => {
    if (sidebarOpen && sessions.length === 0) {
      loadSessions();
    }
  }, [sidebarOpen]);

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
      setApprovalRequest({
        id: 'approval-' + Date.now(),
        title: 'Action Approval Required',
        command: pendingAction.description || pendingAction.type || 'Unknown action',
        riskLevel: pendingAction.data?.riskLevel || 'moderate',
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

  const handleApprove = () => {
    confirmAction?.();
    setShowApprovalModal(false);
    setApprovalRequest(null);
  };

  const handleDeny = () => {
    cancelAction?.();
    setShowApprovalModal(false);
    setApprovalRequest(null);
  };

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

  // Parse mission goal from missionState (single goal, convert to array for panel)
  const missionGoals: Goal[] = missionState?.active && missionState?.goal ? [{
    id: 'current-mission',
    title: missionState.goal,
    status: missionState.phase === 'success' ? 'complete' : 
            missionState.phase === 'failed' ? 'failed' : 
            missionState.phase === 'executing' ? 'active' : 'pending',
  }] : [];

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
          <button className="w-full flex items-center gap-2 px-3 py-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded-lg text-sm">
            <Settings className="w-4 h-4" />
            <span>Settings</span>
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

          {/* Center: Agent Selector (compact) */}
          <div className="relative">
            <button
              onClick={() => setShowAgentDropdown(!showAgentDropdown)}
              className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg border border-gray-700"
              disabled={workstationsLoading}
            >
              <span className="text-base">{activeWorkstation ? getOsIcon(activeWorkstation.name, activeWorkstation.description) : '💻'}</span>
              <div className={`w-2 h-2 rounded-full ${
                activeWorkstation?.status === 'online' ? 'bg-green-400' : 
                activeWorkstation?.status === 'offline' ? 'bg-red-400' : 'bg-gray-500'
              }`} />
              <ChevronDown className={`w-3 h-3 text-gray-500 transition-transform ${showAgentDropdown ? 'rotate-180' : ''}`} />
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

          {/* Right: Mode Selector (compact like agent) + Audio */}
          <div className="flex items-center gap-1">
            {/* Mode Selector - single icon with dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowModeDropdown(!showModeDropdown)}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg border transition-colors ${currentModeConfig.color}`}
              >
                {currentModeConfig.icon}
                <ChevronDown className={`w-3 h-3 transition-transform ${showModeDropdown ? 'rotate-180' : ''}`} />
              </button>
              
              {/* Mode Dropdown */}
              {showModeDropdown && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowModeDropdown(false)} />
                  <div className="absolute top-full mt-1 right-0 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 min-w-[180px] py-1">
                    <div className="px-3 py-1.5 text-xs text-gray-500 uppercase">Execution Mode</div>
                    {MODES.map((mode) => (
                      <button
                        key={mode.value}
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
            
            {/* Audio Toggle */}
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
            trace={lastTrace}
            isProcessing={isProcessing}
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

            {/* Controls Row */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
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
    </div>
  );
};

export default AppV3;
