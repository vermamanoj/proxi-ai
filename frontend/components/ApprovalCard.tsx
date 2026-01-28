import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, X, ChevronRight, Mic, Send } from 'lucide-react';

export type ApprovalType = 'binary' | 'choice' | 'freeform' | 'confirm_screenshot';

export interface ApprovalRequest {
  id: string;
  type: ApprovalType;
  title: string;
  description: string;
  options?: string[];           // For 'choice' type
  screenshotUrl?: string;       // For 'confirm_screenshot' type
  placeholder?: string;         // For 'freeform' type
  timeoutSeconds?: number;
  metadata?: any;
}

interface ApprovalCardProps {
  request: ApprovalRequest;
  onApprove: (response: string | boolean) => void;
  onDeny: () => void;
  isListening?: boolean;        // Voice input active
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  request,
  onApprove,
  onDeny,
  isListening = false
}) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [freeformInput, setFreeformInput] = useState('');
  const [showScreenshot, setShowScreenshot] = useState(false);

  const handleApprove = () => {
    switch (request.type) {
      case 'binary':
      case 'confirm_screenshot':
        onApprove(true);
        break;
      case 'choice':
        if (selectedOption) onApprove(selectedOption);
        break;
      case 'freeform':
        if (freeformInput.trim()) onApprove(freeformInput.trim());
        break;
    }
  };

  const canSubmit = () => {
    switch (request.type) {
      case 'binary':
      case 'confirm_screenshot':
        return true;
      case 'choice':
        return selectedOption !== null;
      case 'freeform':
        return freeformInput.trim().length > 0;
    }
  };

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm border border-yellow-500/30 rounded-2xl overflow-hidden shadow-2xl shadow-black/50 animate-in slide-in-from-bottom-4 max-w-lg mx-auto">
      {/* Header */}
      <div className="bg-yellow-500/10 px-4 py-3 flex items-center gap-3 border-b border-yellow-500/20">
        <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-5 h-5 text-yellow-400" />
        </div>
        <h3 className="text-sm font-bold text-yellow-400 flex-1">{request.title}</h3>
        <button
          onClick={onDeny}
          className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-800"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      
      {/* Description - scrollable if long */}
      <div className="px-4 py-3 max-h-32 overflow-y-auto border-b border-gray-800">
        <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-wrap break-words">{request.description}</p>
      </div>

      {/* Screenshot preview (if applicable) */}
      {request.type === 'confirm_screenshot' && request.screenshotUrl && (
        <div className="px-4 py-3 border-b border-gray-800">
          <button
            onClick={() => setShowScreenshot(!showScreenshot)}
            className="w-full text-left"
          >
            <div className="relative rounded-lg overflow-hidden bg-black">
              <img
                src={request.screenshotUrl}
                alt="Screenshot"
                className={`w-full object-cover transition-all ${showScreenshot ? 'max-h-96' : 'max-h-32'}`}
              />
              {!showScreenshot && (
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent flex items-end justify-center pb-2">
                  <span className="text-xs text-gray-400">Tap to expand</span>
                </div>
              )}
            </div>
          </button>
        </div>
      )}

      {/* Choice options */}
      {request.type === 'choice' && request.options && (
        <div className="px-4 py-3 space-y-2">
          {request.options.map((option, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedOption(option)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all text-left ${
                selectedOption === option
                  ? 'border-proxi-accent bg-proxi-accent/10 text-gray-100'
                  : 'border-gray-700 bg-gray-800/50 text-gray-400 hover:border-gray-600'
              }`}
            >
              <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                selectedOption === option ? 'border-proxi-accent' : 'border-gray-600'
              }`}>
                {selectedOption === option && (
                  <div className="w-2 h-2 rounded-full bg-proxi-accent" />
                )}
              </div>
              <span className="text-sm">{option}</span>
            </button>
          ))}
        </div>
      )}

      {/* Freeform input */}
      {request.type === 'freeform' && (
        <div className="px-4 py-3">
          <div className="relative">
            <input
              type="text"
              value={freeformInput}
              onChange={(e) => setFreeformInput(e.target.value)}
              placeholder={request.placeholder || 'Type your response...'}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 pr-10 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-proxi-accent/50"
              onKeyDown={(e) => e.key === 'Enter' && canSubmit() && handleApprove()}
            />
            {isListening && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <Mic className="w-4 h-4 text-red-500 animate-pulse" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="px-4 py-3 flex gap-2 bg-gray-900/50">
        <button
          onClick={onDeny}
          className="flex-1 py-2.5 px-4 border border-gray-600 text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-800 hover:border-gray-500 transition-all"
        >
          Deny
        </button>
        <button
          onClick={handleApprove}
          disabled={!canSubmit()}
          className="flex-1 py-2.5 px-4 bg-green-500 text-white rounded-lg text-sm font-bold hover:bg-green-400 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          <CheckCircle2 className="w-4 h-4" />
          Approve
        </button>
      </div>

      {/* Voice hint */}
      {isListening && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20 flex items-center justify-center gap-2 text-xs text-red-400">
          <Mic className="w-3 h-3 animate-pulse" />
          <span>Listening... say "approve", "deny", or your response</span>
        </div>
      )}
    </div>
  );
};
