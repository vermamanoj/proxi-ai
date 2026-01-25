import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Settings, Mic, MicOff, Send, Camera, Flame, X, CheckCircle2, Loader2, Zap, BrainCircuit, Volume2, VolumeX } from 'lucide-react';
import { useProxiBrain } from './hooks/useProxiBrain';
import { useGeminiLive } from './hooks/useGeminiLive';
import { ChatView } from './components/ChatView';
import { MissionProgress } from './components/MissionProgress';
import { ApprovalCard } from './components/ApprovalCard';
import { ApprovalRequest } from './types';

const App: React.FC = () => {
  // Audio output toggle state
  const [audioEnabled, setAudioEnabled] = useState(true);

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
    logSystemError
  } = useProxiBrain(audioEnabled);

  // Hook 2: Real-time Voice (Live API / WebRTC)
  const { 
    connected: liveConnected, 
    connect: liveConnect, 
    disconnect: liveDisconnect, 
    sendCommand: liveSendCommand,
    volume: liveVolume, 
    logs: liveLogs, 
    activeTool: liveActiveTool 
  } = useGeminiLive();

  const [input, setInput] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [viewMode, setViewMode] = useState<'summary' | 'timeline' | 'full'>('timeline');
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Convert pendingAction to ApprovalRequest format
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
    if (brainStatus === 'idle' && !isRecording) {
      inputRef.current?.focus();
    }
  }, [brainStatus, isRecording]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      // Cancel any ongoing speech so user can proceed immediately
      window.speechSynthesis.cancel();
      
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
      const prompt = input.trim() || "Analyze this image and describe what you see.";
      sendVisionCommand(file, prompt);
      setInput('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleVoiceToggle = () => {
    if (liveConnected) {
      setIsRecording(!isRecording);
    } else {
      liveConnect();
      setIsRecording(true);
    }
  };

  const triggerChaos = async () => {
    try {
      const res = await fetch('/api/demo/trigger_chaos', { method: 'POST' });
      if (!res.ok) throw new Error(`Failed: ${res.status}`);
      sendCommand("System Alert: High CPU detected. Check system health and fix the issue.");
    } catch (e: any) {
      logSystemError(`Failed to trigger incident: ${e.message}`);
    }
  };

  return (
    <div className="h-screen bg-proxi-black text-gray-200 flex flex-col font-mono overflow-hidden">
      
      {/* Minimal Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-proxi-dark/90 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className={`w-2.5 h-2.5 rounded-full ${statusColor} ${isProcessing ? 'animate-pulse' : ''}`} />
          <h1 className="text-lg font-bold tracking-wider">
            PROXI<span className="text-proxi-accent">.OS</span>
          </h1>
        </div>
        
        <div className="flex items-center gap-2">
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

          {/* Demo trigger - only show in demo mode */}
          <button
            onClick={triggerChaos}
            className="p-2 text-orange-500/70 hover:text-orange-500 hover:bg-orange-500/10 rounded-lg transition-colors"
            title="Trigger Demo Incident"
          >
            <Flame className="w-5 h-5" />
          </button>
          
          {/* Settings */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <Settings className="w-5 h-5" />
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
            
            {/* Mode Toggle */}
            <div className="space-y-4">
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
              
              {/* Voice Uplink */}
              <div>
                <label className="text-xs text-gray-500 uppercase tracking-wider">Voice Uplink</label>
                <button
                  onClick={liveConnected ? liveDisconnect : liveConnect}
                  className={`mt-2 w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                    liveConnected
                      ? 'border-green-500 bg-green-500/10 text-green-400'
                      : 'border-gray-700 bg-gray-800 text-gray-400'
                  }`}
                >
                  <span>{liveConnected ? 'Connected' : 'Disconnected'}</span>
                  <div className={`w-2 h-2 rounded-full ${liveConnected ? 'bg-green-500' : 'bg-gray-600'}`} />
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

      {/* Mission Progress (shows when there are steps) */}
      {lastTrace.length > 0 && (
        <MissionProgress
          trace={lastTrace}
          isProcessing={isProcessing}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      )}

      {/* Main Chat Area */}
      <main className="flex-1 overflow-hidden">
        {viewMode === 'full' ? (
          <ChatView trace={lastTrace} isProcessing={isProcessing} />
        ) : (
          <div className="h-full flex items-center justify-center text-gray-600 p-8">
            <p className="text-sm text-center">
              {isProcessing ? 'Processing your request...' : 'Switch to Full view to see complete trace'}
            </p>
          </div>
        )}
      </main>

      {/* Approval Card Overlay */}
      {approvalRequest && (
        <div className="absolute bottom-20 left-4 right-4 z-30">
          <ApprovalCard
            request={approvalRequest}
            onApprove={() => confirmAction()}
            onDeny={() => cancelAction()}
            isListening={isRecording}
          />
        </div>
      )}

      {/* Input Area */}
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
            className="p-3 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded-xl transition-colors"
          >
            <Camera className="w-5 h-5" />
          </button>

          {/* Text Input */}
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isProcessing ? "Processing..." : "Ask Proxi anything..."}
              disabled={isProcessing}
              className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-proxi-accent/50 disabled:opacity-50"
            />
            {isProcessing && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Loader2 className="w-4 h-4 text-proxi-accent animate-spin" />
              </div>
            )}
          </div>

          {/* Voice Button */}
          <button
            type="button"
            onClick={handleVoiceToggle}
            className={`p-3 rounded-xl transition-all ${
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : liveConnected
                ? 'bg-green-500/20 text-green-500 border border-green-500/50'
                : 'bg-gray-800 text-gray-400 hover:text-gray-300'
            }`}
          >
            {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>

          {/* Send Button */}
          <button
            type="submit"
            disabled={!input.trim() || isProcessing}
            className="p-3 bg-proxi-accent text-black rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all hover:bg-proxi-accent/80"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </footer>
    </div>
  );
};

export default App;
