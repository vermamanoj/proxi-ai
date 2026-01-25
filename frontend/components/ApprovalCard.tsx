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
    <div className="bg-gray-900 border border-proxi-accent/50 rounded-xl overflow-hidden shadow-lg shadow-proxi-accent/10 animate-in slide-in-from-bottom-4">
      {/* Header */}
      <div className="bg-proxi-accent/10 px-4 py-3 flex items-start gap-3">
        <div className="w-8 h-8 rounded-full bg-proxi-accent/20 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-4 h-4 text-proxi-accent" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-proxi-accent">{request.title}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{request.description}</p>
        </div>
        <button
          onClick={onDeny}
          className="p-1 text-gray-500 hover:text-gray-300 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
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
        {request.type === 'binary' || request.type === 'confirm_screenshot' ? (
          <>
            <button
              onClick={onDeny}
              className="flex-1 py-2.5 px-4 border border-red-500/50 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/10 transition-colors"
            >
              Deny
            </button>
            <button
              onClick={handleApprove}
              className="flex-1 py-2.5 px-4 bg-proxi-accent text-black rounded-lg text-sm font-bold hover:bg-proxi-accent/80 transition-colors"
            >
              Approve
            </button>
          </>
        ) : (
          <>
            <button
              onClick={onDeny}
              className="py-2.5 px-4 border border-gray-700 text-gray-400 rounded-lg text-sm hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApprove}
              disabled={!canSubmit()}
              className="flex-1 py-2.5 px-4 bg-proxi-accent text-black rounded-lg text-sm font-bold hover:bg-proxi-accent/80 transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <span>Submit</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </>
        )}
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
