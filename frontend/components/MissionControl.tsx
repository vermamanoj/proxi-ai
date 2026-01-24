
import React from 'react';
import { MissionState, MissionPhase } from '../types';
import { Ear, BrainCircuit, Hammer, ShieldCheck, Activity, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

interface MissionControlProps {
  missionState: MissionState;
  liveConnected: boolean;
}

export const MissionControl: React.FC<MissionControlProps> = ({ missionState, liveConnected }) => {
  
  // Determine global phase (Ear -> Brain -> Hand -> Shield)
  const currentPhase = liveConnected && !missionState.active ? 'listening' : missionState.phase;

  const getStepStatus = (stepPhase: MissionPhase) => {
     // Returns: 'inactive' | 'active' | 'completed' | 'failed'
     if (currentPhase === 'failed') return 'failed';
     
     const order = ['listening', 'planning', 'executing', 'verifying', 'success'];
     const currentIndex = order.indexOf(currentPhase === 'idle' ? 'listening' : currentPhase);
     const stepIndex = order.indexOf(stepPhase);
     
     if (stepIndex < currentIndex) return 'completed';
     if (stepIndex === currentIndex) return 'active';
     return 'inactive';
  };

  return (
    <div className="flex flex-col gap-4">
      {/* 1. THE PIPELINE BAR */}
      <div className="bg-proxi-dark border border-proxi-gray rounded-lg p-4 relative overflow-hidden">
         {/* Background Grid */}
         <div className="absolute inset-0 opacity-10 pointer-events-none" 
              style={{ backgroundImage: 'radial-gradient(#333 1px, transparent 1px)', backgroundSize: '20px 20px' }} 
         />
         
         <div className="relative z-10 flex justify-between items-center gap-2">
            
            {/* STAGE 1: EAR */}
            <PipelineStage 
               icon={Ear} 
               label="UPLINK" 
               status={getStepStatus('listening')} 
               activeColor="text-proxi-accent"
               pulseColor="bg-proxi-accent"
            />
            
            <Connector active={getStepStatus('planning') !== 'inactive'} />
            
            {/* STAGE 2: BRAIN */}
            <PipelineStage 
               icon={BrainCircuit} 
               label="HIVE MIND" 
               status={getStepStatus('planning')} 
               activeColor="text-purple-400"
               pulseColor="bg-purple-500"
            />
            
            <Connector active={getStepStatus('executing') !== 'inactive'} />
            
            {/* STAGE 3: HANDS */}
            <PipelineStage 
               icon={Hammer} 
               label="OPERATOR" 
               status={getStepStatus('executing')} 
               activeColor="text-proxi-warning"
               pulseColor="bg-proxi-warning"
            />
            
            <Connector active={getStepStatus('verifying') !== 'inactive'} />
            
            {/* STAGE 4: SHIELD */}
            <PipelineStage 
               icon={ShieldCheck} 
               label="TRUTH LAYER" 
               status={getStepStatus('verifying')} 
               activeColor="text-green-500"
               pulseColor="bg-green-500"
            />
         </div>
      </div>

      {/* 2. THE ACTIVE STATUS CARD */}
      <div className="bg-proxi-dark border border-proxi-gray rounded-lg p-4 min-h-[120px] flex flex-col justify-center relative overflow-hidden">
         {/* Dynamic Content based on Phase */}
         
         {currentPhase === 'listening' && (
             <div className="flex items-center gap-4 animate-fade-in">
                 <div className="w-12 h-12 rounded-full bg-proxi-accent/10 flex items-center justify-center border border-proxi-accent/30">
                     <Activity className="w-6 h-6 text-proxi-accent animate-pulse" />
                 </div>
                 <div>
                     <div className="text-proxi-accent font-bold text-sm tracking-wider">AWAITING COMMAND</div>
                     <div className="text-gray-400 text-xs mt-1">Voice Uplink Active. Listening...</div>
                 </div>
             </div>
         )}

         {currentPhase === 'planning' && (
             <div className="flex items-center gap-4 animate-fade-in">
                 <div className="w-12 h-12 rounded-full bg-purple-500/10 flex items-center justify-center border border-purple-500/30">
                     <BrainCircuit className="w-6 h-6 text-purple-400 animate-pulse-fast" />
                 </div>
                 <div>
                     <div className="text-purple-400 font-bold text-sm tracking-wider">FORMULATING STRATEGY</div>
                     <div className="text-gray-400 text-xs mt-1">Consulting knowledge base & defining success criteria...</div>
                     {missionState.retryCount > 0 && (
                         <div className="text-orange-400 text-[10px] mt-1 font-bold">RETRY ATTEMPT #{missionState.retryCount}</div>
                     )}
                 </div>
             </div>
         )}

         {currentPhase === 'executing' && (
             <div className="flex items-center gap-4 animate-fade-in">
                 <div className="w-12 h-12 rounded-full bg-proxi-warning/10 flex items-center justify-center border border-proxi-warning/30">
                     <Hammer className="w-6 h-6 text-proxi-warning animate-bounce" />
                 </div>
                 <div className="flex-1">
                     <div className="text-proxi-warning font-bold text-sm tracking-wider">EXECUTING TOOL</div>
                     <div className="text-white font-mono text-xs mt-1 bg-black/40 p-1.5 rounded border border-white/10 truncate">
                         {missionState.activeTool || "Running..."}
                     </div>
                 </div>
             </div>
         )}

         {currentPhase === 'verifying' && (
             <div className="flex items-center gap-4 animate-fade-in">
                 <div className="w-12 h-12 rounded-full bg-blue-500/10 flex items-center justify-center border border-blue-500/30">
                     <ShieldCheck className="w-6 h-6 text-blue-400 animate-pulse" />
                 </div>
                 <div>
                     <div className="text-blue-400 font-bold text-sm tracking-wider">AUDITING RESULTS</div>
                     <div className="text-gray-400 text-xs mt-1">Comparing system state against criteria...</div>
                 </div>
             </div>
         )}

        {/* Verification Outcomes */}
         {missionState.verification.status === 'success' && (
             <div className="flex items-center gap-4 animate-fade-in bg-green-900/10 -m-4 p-6 h-full">
                 <CheckCircle className="w-8 h-8 text-green-500" />
                 <div>
                     <div className="text-green-500 font-bold text-sm tracking-wider">MISSION VERIFIED</div>
                     <div className="text-green-200/70 text-xs mt-1">{missionState.verification.reason}</div>
                 </div>
             </div>
         )}
         
         {missionState.verification.status === 'failed' && (
             <div className="flex items-center gap-4 animate-fade-in bg-red-900/10 -m-4 p-6 h-full">
                 <AlertCircle className="w-8 h-8 text-red-500" />
                 <div>
                     <div className="text-red-500 font-bold text-sm tracking-wider">VERIFICATION FAILED</div>
                     <div className="text-red-200/70 text-xs mt-1">{missionState.verification.reason}</div>
                     <div className="text-xs text-red-400 mt-1 font-mono">Initiating self-correction protocol...</div>
                 </div>
             </div>
         )}
      </div>
    </div>
  );
};

// --- SUBCOMPONENTS ---

const PipelineStage: React.FC<{ icon: any, label: string, status: string, activeColor: string, pulseColor: string }> = ({ icon: Icon, label, status, activeColor, pulseColor }) => {
    const isActive = status === 'active';
    const isCompleted = status === 'completed';
    const isFailed = status === 'failed';
    
    return (
        <div className={`flex flex-col items-center gap-2 z-10 transition-all duration-500 ${isActive ? 'scale-110' : 'opacity-60 grayscale'}`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors relative
                ${isActive ? `border-${activeColor.split('-')[1]} bg-black shadow-[0_0_15px_rgba(0,0,0,0.5)]` : 
                  isCompleted ? 'border-gray-500 bg-gray-800' : 'border-gray-700 bg-black'}
            `}>
                <Icon className={`w-5 h-5 ${isActive ? activeColor : isCompleted ? 'text-gray-400' : 'text-gray-600'}`} />
                
                {/* Ping Animation for Active State */}
                {isActive && (
                    <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping ${pulseColor}`}></span>
                )}
            </div>
            <div className={`text-[10px] font-bold tracking-widest ${isActive ? activeColor : 'text-gray-600'}`}>
                {label}
            </div>
        </div>
    );
};

const Connector: React.FC<{ active: boolean }> = ({ active }) => (
    <div className={`h-0.5 flex-1 transition-colors duration-500 ${active ? 'bg-gray-500' : 'bg-gray-800'}`} />
);
