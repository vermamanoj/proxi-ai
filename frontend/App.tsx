
import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Terminal, Activity, Square, Play, Zap, BrainCircuit, Camera, Mic, MicOff, MousePointerClick, X, GitGraph, Eye, EyeOff, Flame } from 'lucide-react';
import { useProxiBrain } from './hooks/useProxiBrain';
import { useGeminiLive } from './hooks/useGeminiLive';
import { Visualizer } from './components/Visualizer';
import { LogView } from './components/LogView';
import { TraceView } from './components/TraceView';
import { MissionControl } from './components/MissionControl';
import { SystemStatus } from './components/SystemStatus';

const App: React.FC = () => {
  // Hook 1: Text & Vision (REST API)
  const { 
    status: brainStatus, 
    logs: brainLogs, 
    lastTrace,
    complexity,
    pendingAction,
    missionState,
    sendCommand, 
    sendVisionCommand,
    toggleComplexity,
    confirmAction,
    cancelAction,
    logSystemError
  } = useProxiBrain();

  // Hook 2: Real-time Voice (Live API / WebRTC)
  const { 
    connected: liveConnected, 
    connect: liveConnect, 
    disconnect: liveDisconnect, 
    sendCommand: liveSendCommand, // New function to inject text into voice stream
    volume: liveVolume, 
    logs: liveLogs, 
    activeTool: liveActiveTool 
  } = useGeminiLive();

  const [input, setInput] = useState('');
  const [micEnabled, setMicEnabled] = useState(true);
  const [viewMode, setViewMode] = useState<'terminal' | 'trace'>('terminal');
  const [showThoughts, setShowThoughts] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Merge logs from both systems
  const allLogs = useMemo(() => {
    return [...brainLogs, ...liveLogs].sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
  }, [brainLogs, liveLogs]);

  // Combined Status Logic
  const globalStatus = pendingAction ? 'AWAITING_APPROVAL' : liveConnected ? 'UPLINK_ACTIVE' : brainStatus === 'idle' ? 'STANDBY' : brainStatus.toUpperCase();

  useEffect(() => {
    if (globalStatus === 'STANDBY') {
      inputRef.current?.focus();
    }
  }, [globalStatus]);

  useEffect(() => {
      if (lastTrace.length > 0) {
          setViewMode('trace');
      }
  }, [lastTrace]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
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
      const prompt = input.trim() || "Analyze this image and provide a technical assessment.";
      sendVisionCommand(file, prompt);
      setInput('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const triggerChaos = async () => {
      try {
          const res = await fetch('/api/demo/trigger_chaos', { method: 'POST' });
          if (!res.ok) throw new Error(`Chaos Failed: ${res.status}`);
          
          if (liveConnected) {
              // Route through Live Uplink so user can reply via Voice
              liveSendCommand("System Alert: High severity incident detected. Perform a system health check immediately.");
          } else {
              // Fallback to text mode, but warn user
              sendCommand("Proxi, perform a system health check immediately.");
              logSystemError("Uplink Inactive. To interact via voice during incidents, please INITIATE UPLINK first.");
          }
      } catch (e: any) {
          console.error(e);
          logSystemError(`Failed to trigger incident: ${e.message}. Is backend running?`);
      }
  };

  return (
    <div className="min-h-screen bg-proxi-black text-gray-200 flex flex-col font-mono selection:bg-proxi-accent selection:text-proxi-black overflow-hidden">
      {/* Header */}
      <header className="border-b border-proxi-gray bg-proxi-dark/80 backdrop-blur-md p-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${liveConnected ? 'bg-proxi-success shadow-[0_0_10px_#00ff9d] animate-pulse' : 'bg-proxi-gray'}`} />
            <h1 className="text-xl font-bold tracking-widest text-white">PROXI<span className="text-proxi-accent">.OS</span></h1>
            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded">v2.1.0-GHOST</span>
          </div>
          <div className="flex items-center gap-4">
             {/* Uplink Control */}
             <button
              onClick={liveConnected ? liveDisconnect : liveConnect}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-bold transition-all ${
                liveConnected 
                  ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/50' 
                  : 'bg-proxi-accent/10 text-proxi-accent hover:bg-proxi-accent/20 border border-proxi-accent/50'
              }`}
            >
              {liveConnected ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              {liveConnected ? 'TERMINATE UPLINK' : 'INITIATE UPLINK'}
            </button>

             {/* Complexity Toggle */}
             <button 
                onClick={toggleComplexity}
                className={`flex items-center gap-2 px-3 py-1.5 rounded border transition-all text-xs font-bold ${
                  complexity === 'deep' 
                    ? 'bg-purple-500/10 border-purple-500 text-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-500'
                }`}
             >
                {complexity === 'deep' ? <BrainCircuit className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
                {complexity === 'deep' ? 'DEEP THOUGHT' : 'REFLEX MODE'}
             </button>
             
             {/* DEMO TRIGGER */}
             <button 
                onClick={triggerChaos}
                className="flex items-center gap-2 px-3 py-1.5 rounded border border-orange-500/50 bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 transition-all text-xs font-bold"
                title="Simulate Incident (Demo)"
             >
                <Flame className="w-3 h-3" />
                <span>TRIGGER INCIDENT</span>
             </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-140px)] overflow-hidden">
        
        {/* Left Column: Visualizer & Controls (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6 h-full overflow-y-auto pr-2 custom-scrollbar">
          
          {/* Main Visualizer Card */}
          <div className="bg-proxi-dark border border-proxi-gray rounded-lg p-6 relative overflow-hidden group shrink-0">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-proxi-accent to-transparent opacity-50" />
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-sm font-bold text-gray-400 flex items-center gap-2">
                <Activity className="w-4 h-4 text-proxi-accent" />
                {liveConnected ? 'AUDIO STREAM (WEBRTC)' : 'VOICE SYNTHESIS (TTS)'}
              </h2>
              {liveConnected && (
                <button 
                  onClick={() => setMicEnabled(!micEnabled)}
                  className={`p-1.5 rounded hover:bg-white/5 transition-colors ${!micEnabled ? 'text-red-500' : 'text-proxi-success'}`}
                >
                   {micEnabled ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                </button>
              )}
            </div>

            <div className="h-48 bg-black/50 rounded border border-proxi-gray/50 flex items-center justify-center relative">
               <Visualizer 
                  active={liveConnected || brainStatus === 'speaking'} 
                  volume={liveConnected ? liveVolume : 0} 
               />
               <div className="absolute inset-0 pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
               
               {!liveConnected && brainStatus === 'idle' && !pendingAction && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <span className="text-[10px] text-gray-600 tracking-widest">OFFLINE</span>
                  </div>
               )}
            </div>

            <div className="mt-4 flex justify-between text-xs text-gray-500 font-mono">
              <span>STATUS: {globalStatus}</span>
              <span>LATENCY: {liveConnected ? '45ms' : '12ms'}</span>
            </div>
          </div>

          {/* MISSION CONTROL CENTER (The New UI) */}
          <MissionControl missionState={missionState} liveConnected={liveConnected} />
          
          <SystemStatus 
            connected={liveConnected} 
            processing={brainStatus === 'processing' || !!liveActiveTool} 
            analyzing={brainStatus === 'analyzing_visuals'}
          />
          
          {pendingAction && (
            <div className="bg-proxi-dark border border-proxi-accent rounded-lg p-4 animate-pulse relative overflow-hidden shadow-[0_0_20px_rgba(0,240,255,0.2)]">
                <div className="flex items-start gap-3">
                    <MousePointerClick className="w-6 h-6 text-proxi-accent mt-1" />
                    <div className="flex-1">
                        <h3 className="text-proxi-accent font-bold text-sm uppercase tracking-wider mb-1">Authorization Required</h3>
                        <p className="text-gray-300 text-xs mb-3">{pendingAction.description}</p>
                        <div className="flex gap-2">
                            <button 
                                onClick={confirmAction}
                                className="flex-1 bg-proxi-accent text-proxi-black font-bold py-1.5 px-3 rounded text-xs hover:bg-proxi-accent/80 transition-colors uppercase"
                            >
                                Confirm
                            </button>
                            <button 
                                onClick={cancelAction}
                                className="bg-red-500/20 border border-red-500/50 text-red-500 py-1.5 px-2 rounded hover:bg-red-500/30 transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
          )}

        </div>

        {/* Right Column: Terminal/Logs/Trace (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col bg-proxi-dark border border-proxi-gray rounded-lg overflow-hidden relative h-full max-h-[calc(100vh-160px)]">
          {/* Header with Toggles */}
          <div className="bg-proxi-gray/30 p-3 border-b border-proxi-gray flex items-center justify-between shrink-0">
            <div className="flex gap-4">
                <button 
                    onClick={() => setViewMode('terminal')}
                    className={`flex items-center gap-2 text-sm transition-colors ${viewMode === 'terminal' ? 'text-proxi-accent' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    <Terminal className="w-4 h-4" />
                    <span>TERMINAL_OUTPUT</span>
                </button>
                <button 
                    onClick={() => setViewMode('trace')}
                    className={`flex items-center gap-2 text-sm transition-colors ${viewMode === 'trace' ? 'text-proxi-accent' : 'text-gray-500 hover:text-gray-300'}`}
                >
                    <GitGraph className="w-4 h-4" />
                    <span>NEURAL_TRACE</span>
                </button>
                {viewMode === 'trace' && (
                  <button 
                      onClick={() => setShowThoughts(!showThoughts)}
                      className={`flex items-center gap-2 text-xs border rounded px-2 py-0.5 transition-colors ${showThoughts ? 'border-purple-500 text-purple-400 bg-purple-500/10' : 'border-gray-700 text-gray-500'}`}
                  >
                      {showThoughts ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                      <span>INTERNAL_MONOLOGUE</span>
                  </button>
                )}
            </div>
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
              <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden relative bg-black/40 min-h-0">
            {viewMode === 'terminal' ? (
                <LogView logs={allLogs} />
            ) : (
                <TraceView trace={lastTrace} showThoughts={showThoughts} />
            )}
             <div className="absolute inset-0 pointer-events-none" 
                  style={{
                    backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))',
                    backgroundSize: '100% 2px, 3px 100%'
                  }} 
             />
          </div>
        </div>

      </main>

      {/* Footer Input Area */}
      <footer className="fixed bottom-0 left-0 w-full bg-proxi-dark border-t border-proxi-gray p-4 z-40 shadow-[0_-5px_20px_rgba(0,0,0,0.5)]">
        <div className="max-w-7xl mx-auto">
            <form onSubmit={handleSubmit} className="flex gap-3 items-center font-mono">
                <div className="text-proxi-accent font-bold text-lg">{'>'}</div>
                
                <input 
                    ref={inputRef}
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={liveConnected ? "Voice Uplink Active. Speak now..." : "Enter system command or upload visual..."}
                    className="flex-1 bg-transparent border-none outline-none text-gray-100 placeholder-gray-700 focus:ring-0 text-lg"
                    autoComplete="off"
                    spellCheck="false"
                />
                
                <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleFileSelect} 
                    className="hidden" 
                    accept="image/*"
                />

                <button 
                    type="button"
                    onClick={triggerFileUpload}
                    className="p-2 text-proxi-accent/70 hover:text-proxi-accent transition-colors disabled:opacity-30"
                    title="Upload Visual for Analysis"
                >
                    <Camera className="w-5 h-5" />
                </button>
                
                <button 
                    type="submit"
                    disabled={!input.trim()}
                    className="ml-2 px-4 py-2 text-proxi-black bg-proxi-accent rounded hover:bg-proxi-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-bold uppercase text-xs tracking-wider"
                >
                    SEND
                </button>
            </form>
        </div>
      </footer>
    </div>
  );
};

export default App;
