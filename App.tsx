import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Terminal, Cpu, Activity, Github, Cloud, Mic, MicOff, Volume2 } from 'lucide-react';
import { useGeminiLive } from './hooks/useGeminiLive';
import { Visualizer } from './components/Visualizer';
import { LogView } from './components/LogView';
import { LogEntry } from './types';
import { ToolStatus } from './components/ToolStatus';
import { SystemStatus } from './components/SystemStatus';

const App: React.FC = () => {
  const { 
    connected, 
    connect, 
    disconnect, 
    volume, 
    logs, 
    activeTool 
  } = useGeminiLive();

  const [micEnabled, setMicEnabled] = useState(true);

  return (
    <div className="min-h-screen bg-proxi-black text-gray-200 flex flex-col font-mono selection:bg-proxi-accent selection:text-proxi-black">
      {/* Header */}
      <header className="border-b border-proxi-gray bg-proxi-dark/80 backdrop-blur-md p-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${connected ? 'bg-proxi-success shadow-[0_0_10px_#00ff9d]' : 'bg-red-500'}`} />
            <h1 className="text-xl font-bold tracking-widest text-white">PROXI<span className="text-proxi-accent">.OS</span></h1>
            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded">v0.9.3-BETA</span>
          </div>
          <div className="flex items-center gap-4">
             <div className="hidden md:flex items-center gap-2 text-xs text-gray-400">
                <Cloud className="w-4 h-4" />
                <span>us-central1</span>
             </div>
             <button
              onClick={connected ? disconnect : connect}
              className={`flex items-center gap-2 px-4 py-2 rounded-sm text-sm font-bold transition-all ${
                connected 
                  ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/50' 
                  : 'bg-proxi-accent/10 text-proxi-accent hover:bg-proxi-accent/20 border border-proxi-accent/50'
              }`}
            >
              {connected ? <Square className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {connected ? 'TERMINATE UPLINK' : 'INITIATE UPLINK'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Visualizer & Controls (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Main Visualizer Card */}
          <div className="bg-proxi-dark border border-proxi-gray rounded-lg p-6 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-proxi-accent to-transparent opacity-50" />
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-sm font-bold text-gray-400 flex items-center gap-2">
                <Activity className="w-4 h-4 text-proxi-accent" />
                AUDIO STREAM
              </h2>
              <div className="flex gap-2">
                 <button 
                  onClick={() => setMicEnabled(!micEnabled)}
                  className={`p-2 rounded hover:bg-white/5 transition-colors ${!micEnabled ? 'text-red-500' : 'text-proxi-success'}`}
                  title={micEnabled ? "Mute Mic" : "Unmute Mic"}
                 >
                   {micEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
                 </button>
              </div>
            </div>

            <div className="h-48 bg-black/50 rounded border border-proxi-gray/50 flex items-center justify-center relative">
               {connected ? (
                 <Visualizer volume={volume} active={connected} />
               ) : (
                 <div className="text-center">
                    <div className="text-proxi-gray text-xs mb-2">OFFLINE</div>
                    <div className="w-2 h-2 bg-proxi-gray rounded-full mx-auto animate-pulse" />
                 </div>
               )}
               {/* Overlay Scanlines */}
               <div className="absolute inset-0 pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
            </div>

            <div className="mt-4 flex justify-between text-xs text-gray-500 font-mono">
              <span>BW: 24kHz</span>
              <span>LATENCY: {connected ? '<45ms' : '--'}</span>
            </div>
          </div>

          {/* System Status */}
          <SystemStatus connected={connected} processing={!!activeTool} />

          {/* Tool Execution Status (The "Hands") */}
          <ToolStatus activeTool={activeTool} />
        </div>

        {/* Right Column: Terminal/Logs (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col h-[600px] lg:h-auto bg-proxi-dark border border-proxi-gray rounded-lg overflow-hidden">
          <div className="bg-proxi-gray/30 p-3 border-b border-proxi-gray flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <Terminal className="w-4 h-4 text-proxi-accent" />
              <span>TERMINAL_OUTPUT</span>
            </div>
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/20 border border-red-500/50" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
              <div className="w-3 h-3 rounded-full bg-green-500/20 border border-green-500/50" />
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden relative bg-black/40">
            <LogView logs={logs} />
             {/* Decorative grid overlay */}
             <div className="absolute inset-0 pointer-events-none" 
                  style={{
                    backgroundImage: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))',
                    backgroundSize: '100% 2px, 3px 100%'
                  }} 
             />
          </div>
          
          <div className="p-2 bg-proxi-black border-t border-proxi-gray text-xs text-gray-600 font-mono flex items-center gap-2">
            <span className="text-proxi-accent animate-pulse">▋</span>
            {connected ? 'LISTENING_FOR_COMMANDS...' : 'SYSTEM_STANDBY'}
          </div>
        </div>

      </main>
    </div>
  );
};

export default App;