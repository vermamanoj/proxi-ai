import React, { useState, useRef, useEffect } from 'react';
import { Terminal, Activity, Cloud, Send, Zap, BrainCircuit } from 'lucide-react';
import { useProxiBrain } from './hooks/useProxiBrain';
import { Visualizer } from './components/Visualizer';
import { LogView } from './components/LogView';
import { ToolStatus } from './components/ToolStatus';
import { SystemStatus } from './components/SystemStatus';

const App: React.FC = () => {
  const { 
    status, 
    logs, 
    complexity, 
    sendCommand, 
    toggleComplexity 
  } = useProxiBrain();

  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus input
  useEffect(() => {
    if (status === 'idle') {
      inputRef.current?.focus();
    }
  }, [status]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && status === 'idle') {
      sendCommand(input);
      setInput('');
    }
  };

  return (
    <div className="min-h-screen bg-proxi-black text-gray-200 flex flex-col font-mono selection:bg-proxi-accent selection:text-proxi-black">
      {/* Header */}
      <header className="border-b border-proxi-gray bg-proxi-dark/80 backdrop-blur-md p-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${status !== 'idle' ? 'bg-proxi-success shadow-[0_0_10px_#00ff9d] animate-pulse' : 'bg-proxi-gray'}`} />
            <h1 className="text-xl font-bold tracking-widest text-white">PROXI<span className="text-proxi-accent">.OS</span></h1>
            <span className="text-xs text-gray-500 border border-gray-700 px-2 py-0.5 rounded">v1.0.0-RC1</span>
          </div>
          <div className="flex items-center gap-4">
             <div className="hidden md:flex items-center gap-2 text-xs text-gray-400">
                <Cloud className="w-4 h-4" />
                <span>us-central1</span>
             </div>
             
             {/* Complexity Toggle */}
             <button 
                onClick={toggleComplexity}
                className={`flex items-center gap-2 px-3 py-1.5 rounded border transition-all text-xs font-bold ${
                  complexity === 'deep' 
                    ? 'bg-purple-500/10 border-purple-500 text-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.2)]' 
                    : 'bg-proxi-accent/10 border-proxi-accent text-proxi-accent'
                }`}
             >
                {complexity === 'deep' ? <BrainCircuit className="w-3 h-3" /> : <Zap className="w-3 h-3" />}
                {complexity === 'deep' ? 'MODE: DEEP THOUGHT' : 'MODE: REFLEX'}
             </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 pb-24">
        
        {/* Left Column: Visualizer & Controls (4 Cols) */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          
          {/* Main Visualizer Card */}
          <div className="bg-proxi-dark border border-proxi-gray rounded-lg p-6 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-proxi-accent to-transparent opacity-50" />
            
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-sm font-bold text-gray-400 flex items-center gap-2">
                <Activity className="w-4 h-4 text-proxi-accent" />
                VOICE SYNTHESIS
              </h2>
              {status === 'speaking' && (
                <div className="text-xs text-proxi-success animate-pulse">TRANSMITTING...</div>
              )}
            </div>

            <div className="h-48 bg-black/50 rounded border border-proxi-gray/50 flex items-center justify-center relative">
               <Visualizer active={status === 'speaking'} />
               {/* Overlay Scanlines */}
               <div className="absolute inset-0 pointer-events-none bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
            </div>

            <div className="mt-4 flex justify-between text-xs text-gray-500 font-mono">
              <span>STATUS: {status.toUpperCase()}</span>
              <span>LATENCY: {status === 'processing' ? 'CALCULATING...' : '12ms'}</span>
            </div>
          </div>

          {/* System Status */}
          <SystemStatus connected={true} processing={status === 'processing'} />

          {/* Tool Execution Status (The "Hands") */}
          <ToolStatus activeTool={null} />
        </div>

        {/* Right Column: Terminal/Logs (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col h-[500px] lg:h-auto bg-proxi-dark border border-proxi-gray rounded-lg overflow-hidden relative">
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
        </div>

      </main>

      {/* Footer Input Area */}
      <footer className="fixed bottom-0 left-0 w-full bg-proxi-dark border-t border-proxi-gray p-4 z-40 shadow-[0_-5px_20px_rgba(0,0,0,0.5)]">
        <div className="max-w-7xl mx-auto">
            <form onSubmit={handleSubmit} className="flex gap-3 items-center font-mono">
                {/* Prompt Symbol */}
                <div className="text-proxi-accent font-bold text-lg">{'>'}</div>
                
                <input 
                    ref={inputRef}
                    type="text" 
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={status === 'processing' ? "Processing command..." : "Enter system command..."}
                    disabled={status === 'processing'}
                    className="flex-1 bg-transparent border-none outline-none text-gray-100 placeholder-gray-700 focus:ring-0 text-lg"
                    autoComplete="off"
                    spellCheck="false"
                />
                
                {/* Blinking Cursor Simulation (only visible if input is active) */}
                <div className={`w-3 h-6 bg-proxi-accent/50 ${status === 'idle' ? 'animate-pulse' : 'opacity-0'}`} />

                <button 
                    type="submit"
                    disabled={status === 'processing' || !input.trim()}
                    className="ml-2 px-4 py-2 text-proxi-black bg-proxi-accent rounded hover:bg-proxi-accent/80 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-bold uppercase text-xs tracking-wider"
                >
                    {status === 'processing' ? 'EXEC' : 'SEND'}
                </button>
            </form>
        </div>
      </footer>
    </div>
  );
};

export default App;