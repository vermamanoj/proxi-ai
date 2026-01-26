import React from 'react';
import { Target, Cog, ShieldCheck, CheckCircle2, XCircle, Loader2 } from 'lucide-react';

interface VerificationBadgeProps {
  phase: 'idle' | 'listening' | 'planning' | 'executing' | 'verifying' | 'success' | 'failed';
  goal?: string;
  verificationStatus?: 'pending' | 'checking' | 'success' | 'failed';
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  phase,
  goal,
  verificationStatus = 'pending'
}) => {
  if (phase === 'idle') return null;

  const steps = [
    { id: 'goal', label: 'Goal', icon: Target, active: phase === 'planning' },
    { id: 'execute', label: 'Execute', icon: Cog, active: phase === 'executing' },
    { id: 'verify', label: 'Verify', icon: ShieldCheck, active: phase === 'verifying' || phase === 'success' || phase === 'failed' }
  ];

  const getStepStatus = (stepId: string) => {
    const stepOrder = ['goal', 'execute', 'verify'];
    const currentIdx = phase === 'planning' ? 0 : phase === 'executing' ? 1 : 2;
    const stepIdx = stepOrder.indexOf(stepId);
    
    if (stepIdx < currentIdx) return 'completed';
    if (stepIdx === currentIdx) return 'active';
    return 'pending';
  };

  const getFinalIcon = () => {
    if (phase === 'success' && verificationStatus === 'success') {
      return <CheckCircle2 className="w-4 h-4 text-green-400" />;
    }
    if (phase === 'failed' || verificationStatus === 'failed') {
      return <XCircle className="w-4 h-4 text-red-400" />;
    }
    return null;
  };

  return (
    <div className="bg-gray-900/80 border border-gray-700 rounded-lg px-3 py-2">
      {/* Mini goal display */}
      {goal && (
        <div className="text-xs text-gray-400 mb-2 truncate max-w-[200px]">
          {goal}
        </div>
      )}
      
      {/* Step indicators */}
      <div className="flex items-center gap-1">
        {steps.map((step, idx) => {
          const status = getStepStatus(step.id);
          const Icon = step.icon;
          
          return (
            <React.Fragment key={step.id}>
              <div 
                className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-all ${
                  status === 'completed' 
                    ? 'bg-green-500/20 text-green-400' 
                    : status === 'active'
                    ? 'bg-cyan-500/20 text-cyan-400 ring-1 ring-cyan-500/50'
                    : 'bg-gray-800 text-gray-500'
                }`}
              >
                {status === 'active' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : status === 'completed' ? (
                  <CheckCircle2 className="w-3 h-3" />
                ) : (
                  <Icon className="w-3 h-3" />
                )}
                <span className="hidden sm:inline">{step.label}</span>
              </div>
              
              {idx < steps.length - 1 && (
                <div className={`w-3 h-px ${status === 'completed' ? 'bg-green-500' : 'bg-gray-700'}`} />
              )}
            </React.Fragment>
          );
        })}
        
        {/* Final status indicator */}
        {(phase === 'success' || phase === 'failed') && (
          <div className="ml-2">
            {getFinalIcon()}
          </div>
        )}
      </div>
    </div>
  );
};
