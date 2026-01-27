import React from 'react';
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

export interface Goal {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'active' | 'complete' | 'failed';
  result?: string;
}

interface MissionPlanProps {
  goals: Goal[];
  className?: string;
}

export const MissionPlan: React.FC<MissionPlanProps> = ({ goals, className = '' }) => {
  if (!goals || goals.length === 0) return null;

  const getStatusIcon = (status: Goal['status']) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 className="w-4 h-4 text-green-400" />;
      case 'active':
        return <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <Circle className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusColor = (status: Goal['status']) => {
    switch (status) {
      case 'complete':
        return 'border-green-500/30 bg-green-500/5';
      case 'active':
        return 'border-yellow-500/30 bg-yellow-500/5';
      case 'failed':
        return 'border-red-500/30 bg-red-500/5';
      default:
        return 'border-gray-700 bg-gray-800/50';
    }
  };

  const completedCount = goals.filter(g => g.status === 'complete').length;
  const progress = (completedCount / goals.length) * 100;

  return (
    <div className={`bg-gray-900/50 border border-gray-800 rounded-lg p-3 ${className}`}>
      {/* Header with progress */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Mission Plan
        </span>
        <span className="text-xs text-gray-500">
          {completedCount}/{goals.length} complete
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-800 rounded-full mb-3 overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-proxi-accent to-green-400 transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Goals list */}
      <div className="space-y-2">
        {goals.map((goal) => (
          <div
            key={goal.id}
            className={`flex items-start gap-2 p-2 rounded border transition-all ${getStatusColor(goal.status)}`}
          >
            <div className="mt-0.5 shrink-0">
              {getStatusIcon(goal.status)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-500">{goal.id}</span>
                <span className={`text-sm ${goal.status === 'complete' ? 'text-green-300' : goal.status === 'active' ? 'text-yellow-300' : 'text-gray-300'}`}>
                  {goal.title}
                </span>
              </div>
              {goal.description && (
                <p className="text-xs text-gray-500 mt-0.5">{goal.description}</p>
              )}
              {goal.result && (
                <p className="text-xs text-green-400/80 mt-1 italic">✓ {goal.result}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
