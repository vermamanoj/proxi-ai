import React, { useState, useEffect } from 'react';
import { AlertTriangle, Shield, ShieldAlert, ShieldX, CheckCircle2, X, Clock, Terminal } from 'lucide-react';

export type RiskLevel = 'safe' | 'moderate' | 'high' | 'blocked';

export interface ApprovalModalRequest {
  id: string;
  title: string;
  command: string;
  riskLevel: RiskLevel;
  reason: string;
  timeoutSeconds?: number;
  metadata?: Record<string, any>;
}

interface ApprovalModalProps {
  request: ApprovalModalRequest;
  onApprove: () => void;
  onDeny: () => void;
  isOpen: boolean;
}

const RISK_CONFIG = {
  safe: {
    color: 'green',
    icon: Shield,
    label: 'SAFE',
    bgClass: 'bg-green-500/10',
    borderClass: 'border-green-500/30',
    textClass: 'text-green-400',
    iconBg: 'bg-green-500/20',
  },
  moderate: {
    color: 'yellow',
    icon: ShieldAlert,
    label: 'MODERATE',
    bgClass: 'bg-yellow-500/10',
    borderClass: 'border-yellow-500/30',
    textClass: 'text-yellow-400',
    iconBg: 'bg-yellow-500/20',
  },
  high: {
    color: 'red',
    icon: ShieldX,
    label: 'HIGH RISK',
    bgClass: 'bg-red-500/10',
    borderClass: 'border-red-500/30',
    textClass: 'text-red-400',
    iconBg: 'bg-red-500/20',
  },
  blocked: {
    color: 'red',
    icon: X,
    label: 'BLOCKED',
    bgClass: 'bg-red-900/20',
    borderClass: 'border-red-900/50',
    textClass: 'text-red-500',
    iconBg: 'bg-red-900/30',
  },
};

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  request,
  onApprove,
  onDeny,
  isOpen,
}) => {
  const [timeLeft, setTimeLeft] = useState(request.timeoutSeconds || 30);
  const config = RISK_CONFIG[request.riskLevel];
  const Icon = config.icon;

  // Countdown timer
  useEffect(() => {
    if (!isOpen) return;
    
    setTimeLeft(request.timeoutSeconds || 30);
    
    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          onDeny(); // Auto-decline on timeout
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, request.timeoutSeconds, onDeny]);

  if (!isOpen) return null;

  // Blocked commands cannot be approved
  const isBlocked = request.riskLevel === 'blocked';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onDeny}
      />

      {/* Modal */}
      <div className={`relative w-full max-w-md rounded-2xl border ${config.borderClass} ${config.bgClass} bg-gray-900 shadow-2xl animate-in zoom-in-95 fade-in duration-200`}>
        {/* Header */}
        <div className={`px-6 py-4 border-b ${config.borderClass} flex items-center gap-4`}>
          <div className={`w-12 h-12 rounded-xl ${config.iconBg} flex items-center justify-center`}>
            {isBlocked ? (
              <X className={`w-6 h-6 ${config.textClass}`} />
            ) : (
              <AlertTriangle className={`w-6 h-6 ${config.textClass}`} />
            )}
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-bold text-white">
              {isBlocked ? 'Action Blocked' : 'Action Requires Approval'}
            </h2>
            <div className={`inline-flex items-center gap-1.5 mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bgClass} ${config.textClass}`}>
              <Icon className="w-3 h-3" />
              {config.label}
            </div>
          </div>
          <button
            onClick={onDeny}
            className="p-2 text-gray-500 hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-gray-300 text-sm">
            {isBlocked 
              ? 'This action has been blocked for safety reasons:'
              : 'The agent wants to execute the following command:'
            }
          </p>

          {/* Command display */}
          <div className="bg-black rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-2 text-gray-500 text-xs mb-2">
              <Terminal className="w-3.5 h-3.5" />
              <span>Command</span>
            </div>
            <code className="text-proxi-accent text-sm font-mono break-all">
              {request.command}
            </code>
          </div>

          {/* Risk reason */}
          <div className={`p-3 rounded-lg ${config.bgClass} border ${config.borderClass}`}>
            <p className={`text-sm ${config.textClass}`}>
              <span className="font-medium">Reason:</span> {request.reason}
            </p>
          </div>

          {/* Metadata if present */}
          {request.metadata && Object.keys(request.metadata).length > 0 && (
            <div className="text-xs text-gray-500">
              <details>
                <summary className="cursor-pointer hover:text-gray-400">
                  View details
                </summary>
                <pre className="mt-2 p-2 bg-black rounded text-gray-400 overflow-auto max-h-32">
                  {JSON.stringify(request.metadata, null, 2)}
                </pre>
              </details>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className={`px-6 py-4 border-t ${config.borderClass} space-y-3`}>
          {/* Timer */}
          {!isBlocked && (
            <div className="flex items-center justify-center gap-2 text-gray-500 text-sm">
              <Clock className="w-4 h-4" />
              <span>Auto-decline in: <span className={timeLeft <= 10 ? 'text-red-400 font-bold' : ''}>{timeLeft}s</span></span>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onDeny}
              className="flex-1 py-3 px-4 border border-gray-700 text-gray-300 rounded-xl font-medium hover:bg-gray-800 transition-colors"
            >
              {isBlocked ? 'Close' : 'Deny'}
            </button>
            {!isBlocked && (
              <button
                onClick={onApprove}
                className="flex-1 py-3 px-4 bg-proxi-accent text-black rounded-xl font-bold hover:bg-proxi-accent/90 transition-colors flex items-center justify-center gap-2"
              >
                <CheckCircle2 className="w-5 h-5" />
                Approve
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApprovalModal;
