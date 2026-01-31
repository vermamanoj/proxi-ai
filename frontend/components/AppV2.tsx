// AppV2.tsx - Redesigned UI with simplified UX
// Access via /#/v2 route

import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, Camera, X, Loader2, Zap, Volume2, VolumeX, LogOut, Plus, 
  Monitor, Menu, Square, Mic, MicOff, ChevronDown
} from 'lucide-react';
import { useProxiBrain } from '../hooks/useProxiBrain';
import { useGeminiLive } from '../hooks/useGeminiLive';
import { useAuth } from '../hooks/useAuth';
import { useWorkstations } from '../hooks/useWorkstations';
import { ChatView } from './ChatView';
import { Complexity, MessageSource } from '../types';

// Mode configurations for display
const MODES: { value: Complexity; label: string; icon: string; color: string }[] = [
  { value: 'plan', label: 'Plan', icon: '📋', color: 'text-purple-400 bg-purple-500/20 border-purple-500/50' },
  { value: 'quick', label: 'Quick', icon: '⚡', color: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/50' },
  { value: 'balanced', label: 'Auto', icon: '⚖️', color: 'text-blue-400 bg-blue-500/20 border-blue-500/50' },
  { value: 'thorough', label: 'Deep', icon: '🔬', color: 'text-green-400 bg-green-500/20 border-green-500/50' },
];

export const AppV2: React.FC = () => {
  const { logout } = useAuth();
  const [audioEnabled, setAudioEnabled] = useState(true);
  const { activeWorkstation, workstations, setActiveWorkstation, isLoading: workstationsLoading } = useWorkstations();
  
  // Mode state - lifted up for visibility
  const [currentMode, setCurrentMode] = useState<Complexity>('balanced');
  const [showModeDropdown, setShowModeDropdown] = useState(false);

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

  // Use lastTrace from brain (useGeminiLive doesn't expose trace separately)
  const displayTrace = lastTrace;

  // Input state
  const [input, setInput] = useState('');
  const [stagedImage, setStagedImage] = useState<{ file: File; preview: string } | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Status
  const isProcessing = brainStatus === 'processing' || brainStatus === 'speaking';
  const isActivelyProcessing = brainStatus === 'processing';

  // Update execution mode when currentMode changes
  useEffect(() => {
    setExecutionMode(currentMode);
  }, [currentMode, setExecutionMode]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isActivelyProcessing) return;
    
    if (stagedImage) {
      const prompt = input.trim() || "Analyze this image and describe what you see.";
      sendVisionCommand(stagedImage.file, prompt);
      setStagedImage(null);
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
    const file = e.target.files?.[0];
    if (file) {
      setStagedImage({ file, preview: URL.createObjectURL(file) });
    }
  };

  const currentModeConfig = MODES.find(m => m.value === currentMode) || MODES[2];

  return (
    <div className="h-[100dvh] bg-proxi-black text-gray-200 flex flex-col font-mono overflow-hidden">
      <div className="h-full flex flex-col w-full max-w-2xl mx-auto lg:border-x lg:border-gray-800 overflow-hidden">
        
        {/* REDESIGNED HEADER - Option A: Mode Pill visible */}
        <header className="flex items-center justify-between px-3 py-2 border-b border-gray-800 bg-gray-900 shrink-0 z-20">
          {/* Left: Status + Title */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isProcessing ? 'bg-yellow-500 animate-pulse' : liveConnected ? 'bg-green-500' : 'bg-gray-500'}`} />
            <h1 className="text-sm font-bold tracking-wider">
              PROXI<span className="text-proxi-accent">.OS</span>
            </h1>
          </div>

          {/* Center: Mode Pill (NEW - Always Visible) */}
          <div className="relative">
            <button
              onClick={() => setShowModeDropdown(!showModeDropdown)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-medium transition-all ${currentModeConfig.color}`}
            >
              <span>{currentModeConfig.icon}</span>
              <span>{currentModeConfig.label}</span>
              <ChevronDown className="w-3 h-3" />
            </button>
            
            {/* Mode Dropdown */}
            {showModeDropdown && (
              <div className="absolute top-full mt-1 left-1/2 -translate-x-1/2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden min-w-[140px]">
                {MODES.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => {
                      setCurrentMode(mode.value);
                      setShowModeDropdown(false);
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-gray-800 transition-colors ${
                      currentMode === mode.value ? 'bg-gray-800' : ''
                    }`}
                  >
                    <span>{mode.icon}</span>
                    <span>{mode.label}</span>
                    {currentMode === mode.value && <span className="ml-auto text-proxi-accent">✓</span>}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Right: Minimal Actions */}
          <div className="flex items-center gap-1">
            {/* Agent indicator (compact) */}
            <div className="hidden sm:flex items-center gap-1 text-xs text-gray-500 mr-2">
              <Monitor className="w-3 h-3" />
              <span className="truncate max-w-[80px]">{activeWorkstation?.name || 'No agent'}</span>
            </div>
            
            {/* New Session */}
            <button 
              onClick={() => { liveClearSession(); brainClearSession(); }} 
              className="p-2 text-gray-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors" 
              title="New Session"
            >
              <Plus className="w-4 h-4" />
            </button>
            
            {/* Audio */}
            <button
              onClick={() => setAudioEnabled(!audioEnabled)}
              className={`p-2 rounded-lg transition-all ${audioEnabled ? 'text-blue-400' : 'text-gray-500'}`}
              title={audioEnabled ? 'Mute' : 'Unmute'}
            >
              {audioEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            
            {/* Logout */}
            <button onClick={logout} className="p-2 text-gray-500 hover:text-red-400 rounded-lg" title="Logout">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Mode Hint Banner (shows when in Plan mode) */}
        {currentMode === 'plan' && (
          <div className="bg-purple-500/10 border-b border-purple-500/30 px-3 py-1.5 text-xs text-purple-300 flex items-center gap-2">
            <span>📋</span>
            <span>Plan Mode: Agent will show steps without executing. Say "execute" to run.</span>
          </div>
        )}

        {/* Chat Area */}
        <main className="flex-1 overflow-hidden flex flex-col">
          <ChatView trace={displayTrace} isProcessing={isProcessing} />
        </main>

        {/* REDESIGNED INPUT - Option B: Simplified */}
        <footer className="border-t border-gray-800 bg-proxi-dark p-3 shrink-0" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            {/* Camera */}
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
              className={`p-2.5 rounded-xl transition-colors ${
                stagedImage ? 'text-proxi-accent bg-proxi-accent/10' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              <Camera className="w-5 h-5" />
            </button>

            {/* Staged Image Preview (inline, compact) */}
            {stagedImage && (
              <div className="relative shrink-0">
                <img 
                  src={stagedImage.preview} 
                  alt="Staged" 
                  className="w-8 h-8 rounded-lg object-cover border border-proxi-accent"
                />
                <button
                  type="button"
                  onClick={() => setStagedImage(null)}
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
                placeholder={isActivelyProcessing ? "Processing..." : "Ask Proxi..."}
                disabled={isActivelyProcessing}
                rows={1}
                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-proxi-accent/50 disabled:opacity-50 resize-none"
                style={{ minHeight: '40px', maxHeight: '100px' }}
              />
              {isProcessing && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="w-4 h-4 text-proxi-accent animate-spin" />
                </div>
              )}
            </div>

            {/* Action Buttons (simplified: Mic + Send/Stop) */}
            <div className="flex items-center gap-1">
              {/* Mic - compact */}
              <button
                type="button"
                onClick={liveConnected ? toggleMicMute : liveConnect}
                className={`p-2.5 rounded-xl transition-all ${
                  !liveConnected
                    ? 'bg-gray-800 text-gray-500 hover:text-gray-300'
                    : micMuted
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-green-500/20 text-green-400'
                }`}
                title={!liveConnected ? 'Connect Voice' : micMuted ? 'Unmute' : 'Mute'}
              >
                {micMuted || !liveConnected ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              </button>

              {/* Send or Stop */}
              {isProcessing ? (
                <button
                  type="button"
                  onClick={stopExecution}
                  className="p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600"
                  title="Stop"
                >
                  <Square className="w-5 h-5 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isActivelyProcessing || (!input.trim() && !stagedImage)}
                  className="p-2.5 bg-proxi-accent text-black rounded-xl disabled:opacity-30 disabled:cursor-not-allowed hover:bg-proxi-accent/80"
                >
                  <Send className="w-5 h-5" />
                </button>
              )}
            </div>
          </form>
        </footer>

      </div>
      
      {/* Click outside to close mode dropdown */}
      {showModeDropdown && (
        <div 
          className="fixed inset-0 z-40" 
          onClick={() => setShowModeDropdown(false)}
        />
      )}
    </div>
  );
};

export default AppV2;
