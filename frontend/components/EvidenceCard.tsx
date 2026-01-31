import React, { useState } from 'react';
import { ChevronDown, ChevronUp, FileText, Image, Terminal, CheckCircle2 } from 'lucide-react';

interface EvidenceCardProps {
  evidenceId: string;
  claim: string;
  evidenceType?: string;
  data?: string;
  imageUrl?: string;
  confidence?: string;
  timestamp?: string;
  defaultExpanded?: boolean;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  evidenceId,
  claim,
  evidenceType = 'text',
  data,
  imageUrl,
  confidence = 'medium',
  timestamp,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const getIcon = () => {
    switch (evidenceType) {
      case 'screenshot':
      case 'image':
        return <Image className="w-4 h-4" />;
      case 'command_output':
      case 'terminal':
        return <Terminal className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getConfidenceColor = () => {
    switch (confidence) {
      case 'high':
        return 'text-green-400 bg-green-900/30';
      case 'medium':
        return 'text-yellow-400 bg-yellow-900/30';
      case 'low':
        return 'text-orange-400 bg-orange-900/30';
      default:
        return 'text-gray-400 bg-gray-900/30';
    }
  };

  return (
    <div className="my-2 rounded-lg border border-gray-700 bg-gray-900/50 overflow-hidden">
      {/* Header - always visible, clickable to expand */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-green-500" />
          <span className="text-sm text-gray-200">{claim}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${getConfidenceColor()}`}>
            #{evidenceId}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {getIcon()}
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-800">
          {/* Image evidence */}
          {imageUrl && (
            <div className="mt-2">
              <img
                src={imageUrl}
                alt={`Evidence ${evidenceId}`}
                className="max-w-full max-h-64 rounded border border-gray-700 object-contain"
              />
            </div>
          )}

          {/* Text/Command output evidence */}
          {data && (
            <div className="mt-2">
              {evidenceType === 'command_output' || evidenceType === 'terminal' ? (
                <pre className="text-xs font-mono bg-black/50 p-2 rounded overflow-x-auto max-h-48 overflow-y-auto text-green-400">
                  {data}
                </pre>
              ) : (
                <div className="text-sm text-gray-300 bg-gray-800/50 p-2 rounded">
                  {data}
                </div>
              )}
            </div>
          )}

          {/* Metadata footer */}
          {timestamp && (
            <div className="mt-2 text-xs text-gray-500">
              Captured: {timestamp}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Helper function to parse evidence from message content
export const parseEvidenceFromMessage = (content: string): {
  hasEvidence: boolean;
  evidenceId?: string;
  claim?: string;
  remainingContent: string;
} => {
  // Pattern: 📎 Evidence #abc123 stored for: [claim]
  const storePattern = /📎\s*Evidence\s*#([a-f0-9]+)\s*stored\s*for:\s*([^(]+?)(?:\s*\(|$)/i;
  const match = content.match(storePattern);

  if (match) {
    return {
      hasEvidence: true,
      evidenceId: match[1],
      claim: match[2].trim(),
      remainingContent: content.replace(storePattern, '').trim(),
    };
  }

  return {
    hasEvidence: false,
    remainingContent: content,
  };
};

// Component to render message content with inline evidence cards
interface MessageWithEvidenceProps {
  content: string;
  imageUrl?: string;
}

export const MessageWithEvidence: React.FC<MessageWithEvidenceProps> = ({ content, imageUrl }) => {
  const parsed = parseEvidenceFromMessage(content);

  if (!parsed.hasEvidence) {
    return <>{content}</>;
  }

  return (
    <div>
      {parsed.remainingContent && (
        <div className="mb-2">{parsed.remainingContent}</div>
      )}
      <EvidenceCard
        evidenceId={parsed.evidenceId!}
        claim={parsed.claim!}
        imageUrl={imageUrl}
        defaultExpanded={false}
      />
    </div>
  );
};

export default EvidenceCard;
