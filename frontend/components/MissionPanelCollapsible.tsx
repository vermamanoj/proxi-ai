import React, { useState, useMemo } from 'react';
import { ChevronDown, CheckCircle2, Circle, Loader2, XCircle, Image, ChevronRight } from 'lucide-react';

export interface Goal {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'active' | 'complete' | 'failed';
  result?: string;
  substeps?: Goal[];
  images?: string[]; // Base64 or URL references
}

interface MissionPanelProps {
  goals: Goal[];
  className?: string;
  onImageClick?: (imageUrl: string) => void;
}

type SectionKey = 'stepper' | 'goals' | 'current' | 'logs';

export const MissionPanelCollapsible: React.FC<MissionPanelProps> = ({ 
  goals, 
  className = '',
  onImageClick 
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<SectionKey>>(
    new Set(['stepper', 'current'])
  );

  const toggleSection = (section: SectionKey) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  // Expand all sections
  const expandAll = () => {
    setExpandedSections(new Set(['stepper', 'goals', 'current']));
  };

  // Derived data
  const completedCount = goals.filter(g => g.status === 'complete').length;
  const failedCount = goals.filter(g => g.status === 'failed').length;
  const activeGoal = goals.find(g => g.status === 'active');
  const activeIndex = activeGoal ? goals.findIndex(g => g.id === activeGoal.id) : -1;
  
  // Check if all sections are collapsed
  const allCollapsed = expandedSections.size === 0;

  if (!goals || goals.length === 0) return null;

  // Compact single-line view when all collapsed
  if (allCollapsed) {
    return (
      <div className={`bg-gray-900/80 backdrop-blur border border-gray-800 rounded-xl overflow-hidden ${className}`}>
        <button
          onClick={expandAll}
          className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-4 text-xs">
            <span className="text-gray-400 uppercase tracking-wider font-semibold">Mission</span>
            <span className="text-gray-500">▸</span>
            <span className="text-gray-400 uppercase tracking-wider font-semibold">Goals</span>
            <span className="text-gray-500">▸</span>
            <span className="text-gray-400 uppercase tracking-wider font-semibold">Steps</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs ${completedCount === goals.length ? 'text-green-400' : 'text-gray-500'}`}>
              {completedCount}/{goals.length}
            </span>
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </div>
        </button>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900/80 backdrop-blur border border-gray-800 rounded-xl overflow-hidden ${className}`}>
      
      {/* Section 1: Mission Header with Horizontal Stepper */}
      <CollapsibleSection
        title="Mission"
        badge={`${completedCount}/${goals.length}`}
        expanded={expandedSections.has('stepper')}
        onToggle={() => toggleSection('stepper')}
        headerClassName="bg-gray-900"
      >
        {/* Horizontal Step Indicator */}
        <div className="px-3 py-2 flex items-center gap-1 overflow-x-auto scrollbar-hide">
          {goals.map((goal, idx) => (
            <React.Fragment key={goal.id}>
              <StepIndicator
                number={idx + 1}
                status={goal.status}
                isActive={goal.status === 'active'}
                compact
              />
              {idx < goals.length - 1 && (
                <ChevronRight className={`w-3 h-3 shrink-0 ${
                  goal.status === 'complete' ? 'text-green-500' : 'text-gray-600'
                }`} />
              )}
            </React.Fragment>
          ))}
        </div>
      </CollapsibleSection>

      {/* Section 2: All Goals List */}
      <CollapsibleSection
        title="Goals"
        badge={failedCount > 0 ? `${failedCount} failed` : undefined}
        badgeColor={failedCount > 0 ? 'text-red-400' : undefined}
        expanded={expandedSections.has('goals')}
        onToggle={() => toggleSection('goals')}
      >
        <div className="px-3 py-2 space-y-1.5 max-h-40 overflow-y-auto">
          {goals.map((goal, idx) => (
            <GoalRow key={goal.id} goal={goal} index={idx + 1} compact />
          ))}
        </div>
      </CollapsibleSection>

      {/* Section 3: Current Step Details */}
      {activeGoal && (
        <CollapsibleSection
          title="Current Step"
          badge={`Step ${activeIndex + 1}`}
          expanded={expandedSections.has('current')}
          onToggle={() => toggleSection('current')}
          accentColor="border-l-yellow-500"
        >
          <div className="px-3 py-2">
            <div className="flex items-start gap-2">
              <Loader2 className="w-4 h-4 text-yellow-400 animate-spin mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-yellow-300">{activeGoal.title}</div>
                {activeGoal.description && (
                  <p className="text-xs text-gray-400 mt-0.5">{activeGoal.description}</p>
                )}
              </div>
            </div>
            
            {/* Substeps for current goal */}
            {activeGoal.substeps && activeGoal.substeps.length > 0 && (
              <div className="mt-2 ml-6 space-y-1 border-l border-gray-700 pl-3">
                {activeGoal.substeps.map((sub, idx) => (
                  <div key={sub.id} className="flex items-center gap-2 text-xs">
                    <StatusIcon status={sub.status} size="sm" />
                    <span className="text-gray-500">{activeIndex + 1}.{idx + 1}</span>
                    <span className={sub.status === 'active' ? 'text-yellow-300' : 'text-gray-400'}>
                      {sub.title}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Images attached to current step */}
            {activeGoal.images && activeGoal.images.length > 0 && (
              <div className="mt-2 flex gap-2 overflow-x-auto">
                {activeGoal.images.map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => onImageClick?.(img)}
                    className="w-16 h-16 rounded border border-gray-700 overflow-hidden shrink-0 hover:border-proxi-accent transition-colors"
                  >
                    <img src={img} alt={`Step ${activeIndex + 1} image ${idx + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        </CollapsibleSection>
      )}
    </div>
  );
};

// --- Subcomponents ---

interface CollapsibleSectionProps {
  title: string;
  badge?: string;
  badgeColor?: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  headerClassName?: string;
  accentColor?: string;
}

const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  badge,
  badgeColor = 'text-gray-500',
  expanded,
  onToggle,
  children,
  headerClassName = '',
  accentColor = ''
}) => (
  <div className={`border-b border-gray-800 last:border-b-0 ${accentColor ? `border-l-2 ${accentColor}` : ''}`}>
    <button
      onClick={onToggle}
      className={`w-full px-3 py-2 flex items-center justify-between hover:bg-gray-800/50 transition-colors ${headerClassName}`}
    >
      <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</span>
      <div className="flex items-center gap-2">
        {badge && <span className={`text-xs ${badgeColor}`}>{badge}</span>}
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} />
      </div>
    </button>
    {expanded && children}
  </div>
);

interface StepIndicatorProps {
  number: number;
  status: Goal['status'];
  isActive?: boolean;
  compact?: boolean;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ number, status, isActive, compact }) => {
  const baseClasses = compact 
    ? 'w-6 h-6 text-xs' 
    : 'w-8 h-8 text-sm';
  
  const statusClasses = {
    complete: 'bg-green-500/20 border-green-500 text-green-400',
    active: 'bg-yellow-500/20 border-yellow-500 text-yellow-400 animate-pulse',
    failed: 'bg-red-500/20 border-red-500 text-red-400',
    pending: 'bg-gray-800 border-gray-600 text-gray-500'
  };

  return (
    <div className={`${baseClasses} rounded-full border flex items-center justify-center font-bold shrink-0 ${statusClasses[status]}`}>
      {status === 'complete' ? (
        <CheckCircle2 className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
      ) : status === 'failed' ? (
        <XCircle className={compact ? 'w-3 h-3' : 'w-4 h-4'} />
      ) : status === 'active' ? (
        <Loader2 className={`${compact ? 'w-3 h-3' : 'w-4 h-4'} animate-spin`} />
      ) : (
        number
      )}
    </div>
  );
};

interface GoalRowProps {
  goal: Goal;
  index: number;
  compact?: boolean;
}

const GoalRow: React.FC<GoalRowProps> = ({ goal, index, compact }) => {
  const statusColors = {
    complete: 'text-green-400',
    active: 'text-yellow-300',
    failed: 'text-red-400',
    pending: 'text-gray-500'
  };

  return (
    <div className={`flex items-start gap-2 ${compact ? 'py-0.5' : 'py-1'}`}>
      <StatusIcon status={goal.status} size={compact ? 'sm' : 'md'} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-600">{index}</span>
          <span className={`text-sm truncate ${statusColors[goal.status]}`}>{goal.title}</span>
        </div>
        {goal.result && goal.status === 'complete' && (
          <p className="text-xs text-green-500/70 mt-0.5 truncate">✓ {goal.result}</p>
        )}
        {goal.result && goal.status === 'failed' && (
          <p className="text-xs text-red-400/70 mt-0.5 truncate">✗ {goal.result}</p>
        )}
      </div>
      {goal.images && goal.images.length > 0 && (
        <div className="flex items-center gap-1 text-gray-500">
          <Image className="w-3 h-3" />
          <span className="text-xs">{goal.images.length}</span>
        </div>
      )}
    </div>
  );
};

interface StatusIconProps {
  status: Goal['status'];
  size?: 'sm' | 'md';
}

const StatusIcon: React.FC<StatusIconProps> = ({ status, size = 'md' }) => {
  const sizeClass = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';
  
  switch (status) {
    case 'complete':
      return <CheckCircle2 className={`${sizeClass} text-green-400 shrink-0`} />;
    case 'active':
      return <Loader2 className={`${sizeClass} text-yellow-400 animate-spin shrink-0`} />;
    case 'failed':
      return <XCircle className={`${sizeClass} text-red-400 shrink-0`} />;
    default:
      return <Circle className={`${sizeClass} text-gray-600 shrink-0`} />;
  }
};

export default MissionPanelCollapsible;
