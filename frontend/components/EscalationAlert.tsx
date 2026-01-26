import React, { useState } from 'react';
import { AlertCircle, Send, X, MessageSquare } from 'lucide-react';

export interface EscalationRequest {
  id: string;
  message: string;
  context?: string;
  timestamp: Date;
  options?: string[];
}

interface EscalationAlertProps {
  request: EscalationRequest;
  onRespond: (response: string) => void;
  onDismiss: () => void;
}

export const EscalationAlert: React.FC<EscalationAlertProps> = ({
  request,
  onRespond,
  onDismiss,
}) => {
  const [response, setResponse] = useState('');
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  const handleSubmit = () => {
    const finalResponse = selectedOption || response.trim();
    if (finalResponse) {
      onRespond(finalResponse);
    }
  };

  return (
    <div className="bg-gradient-to-r from-orange-500/10 to-yellow-500/10 border border-orange-500/30 rounded-xl overflow-hidden animate-in slide-in-from-top-2">
      {/* Header */}
      <div className="px-4 py-3 bg-orange-500/10 border-b border-orange-500/20 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center animate-pulse">
          <AlertCircle className="w-5 h-5 text-orange-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-bold text-orange-400">Agent Needs Your Help</h3>
          <p className="text-xs text-gray-400">Human judgment required</p>
        </div>
        <button
          onClick={onDismiss}
          className="p-1.5 text-gray-500 hover:text-gray-300 transition-colors rounded-lg hover:bg-gray-800"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Message */}
      <div className="px-4 py-4">
        <div className="bg-black/30 rounded-lg p-4 border border-gray-800">
          <div className="flex items-start gap-3">
            <MessageSquare className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
            <p className="text-gray-200 text-sm leading-relaxed">
              {request.message}
            </p>
          </div>
        </div>

        {/* Context if available */}
        {request.context && (
          <p className="text-xs text-gray-500 mt-2 px-1">
            Context: {request.context}
          </p>
        )}
      </div>

      {/* Quick options if available */}
      {request.options && request.options.length > 0 && (
        <div className="px-4 pb-3">
          <p className="text-xs text-gray-500 mb-2">Quick responses:</p>
          <div className="flex flex-wrap gap-2">
            {request.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setSelectedOption(option);
                  setResponse('');
                }}
                className={`px-3 py-1.5 rounded-lg text-sm transition-all ${
                  selectedOption === option
                    ? 'bg-orange-500/20 text-orange-300 border border-orange-500/50'
                    : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Response input */}
      <div className="px-4 pb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={response}
            onChange={(e) => {
              setResponse(e.target.value);
              setSelectedOption(null);
            }}
            placeholder="Type your response to the agent..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          />
          <button
            onClick={handleSubmit}
            disabled={!response.trim() && !selectedOption}
            className="px-4 py-2.5 bg-orange-500 text-white rounded-lg font-medium hover:bg-orange-600 transition-colors disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Timestamp */}
      <div className="px-4 py-2 bg-black/20 border-t border-gray-800 text-center">
        <span className="text-xs text-gray-500">
          Escalated at {request.timestamp.toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
};

export default EscalationAlert;
