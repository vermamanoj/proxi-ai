import React, { useEffect, useState } from 'react';
import { Clock, MessageSquare, ChevronRight, X } from 'lucide-react';
import { getSessions, SessionSummary } from '../services/sessionService';

interface SessionHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSession?: (sessionId: string) => void;
}

export const SessionHistory: React.FC<SessionHistoryProps> = ({ isOpen, onClose, onSelectSession }) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadSessions();
    }
  }, [isOpen]);

  const loadSessions = async () => {
    setLoading(true);
    try {
      const data = await getSessions(20);
      setSessions(data);
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
    setLoading(false);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm" onClick={onClose}>
      <div 
        className="absolute left-0 top-0 h-full w-80 bg-gray-900 border-r border-gray-800 overflow-hidden flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-gray-200">Session History</h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-300 hover:bg-gray-800 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Session List */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-6 h-6 border-2 border-proxi-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-gray-500">
              <MessageSquare className="w-8 h-8 mb-2 opacity-50" />
              <p className="text-sm">No saved sessions yet</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-800">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => onSelectSession?.(session.id)}
                  className="w-full p-4 text-left hover:bg-gray-800/50 transition-colors group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-gray-200 font-medium truncate">
                        {session.title || 'Untitled Session'}
                      </p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(session.updated_at || session.created_at)}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase ${
                          session.status === 'active' 
                            ? 'bg-green-500/20 text-green-400' 
                            : 'bg-gray-700 text-gray-400'
                        }`}>
                          {session.status}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 shrink-0 mt-1" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800 text-center">
          <p className="text-xs text-gray-600">
            Sessions are saved when you click New Session (+)
          </p>
        </div>
      </div>
    </div>
  );
};
