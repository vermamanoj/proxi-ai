import React, { useState } from 'react';
import { ChevronDown, Check, Wifi, WifiOff } from 'lucide-react';
import { useWorkstations } from '../hooks/useWorkstations';

interface AgentSelectorProps {
  className?: string;
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({ className = '' }) => {
  const { workstations, activeWorkstation, setActiveWorkstation, isLoading } = useWorkstations();
  const [isOpen, setIsOpen] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'text-green-400';
      case 'offline': return 'text-red-400';
      case 'starting': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status: string) => {
    return status === 'online' ? (
      <Wifi className="w-3 h-3" />
    ) : (
      <WifiOff className="w-3 h-3" />
    );
  };

  // Get OS icon based on workstation description or name
  const getOsIcon = (ws: { name: string; description?: string }) => {
    const text = `${ws.name} ${ws.description || ''}`.toLowerCase();
    if (text.includes('windows')) return '🪟';
    if (text.includes('linux') || text.includes('ubuntu') || text.includes('docker')) return '🐧';
    if (text.includes('mac')) return '🍎';
    return '💻';
  };

  // Get short display name (first word or abbreviation)
  const getShortName = (name: string) => {
    // If name is short enough, use it
    if (name.length <= 12) return name;
    // Otherwise, take first word or abbreviate
    const firstWord = name.split(' ')[0];
    if (firstWord.length <= 10) return firstWord + '...';
    return firstWord.substring(0, 8) + '...';
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 px-2 py-1.5 bg-gray-800/50 hover:bg-gray-700/50 rounded-lg border border-gray-700 transition-colors"
        disabled={isLoading}
      >
        {/* OS Icon */}
        <span className="text-sm">{activeWorkstation ? getOsIcon(activeWorkstation) : '💻'}</span>
        {/* Short name - hidden on very small screens */}
        <span className="text-xs text-gray-300 hidden sm:inline max-w-[80px] truncate">
          {activeWorkstation ? getShortName(activeWorkstation.name) : 'Agent'}
        </span>
        {/* Status indicator */}
        {activeWorkstation && (
          <span className={getStatusColor(activeWorkstation.status)}>
            {getStatusIcon(activeWorkstation.status)}
          </span>
        )}
        <ChevronDown className={`w-3 h-3 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-40" 
            onClick={() => setIsOpen(false)} 
          />
          <div className="absolute top-full right-0 mt-2 w-72 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
            <div className="p-2 border-b border-gray-800">
              <span className="text-xs text-gray-500 uppercase tracking-wider">Proxi Agents</span>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {workstations.map((ws) => (
                <button
                  key={ws.id}
                  onClick={() => {
                    setActiveWorkstation(ws.id);
                    setIsOpen(false);
                  }}
                  className={`w-full flex items-center gap-3 p-3 hover:bg-gray-800 transition-colors ${
                    activeWorkstation?.id === ws.id ? 'bg-gray-800/50' : ''
                  }`}
                >
                  {/* OS Icon */}
                  <span className="text-lg">{getOsIcon(ws)}</span>
                  {/* Status dot */}
                  <div className={`w-2 h-2 rounded-full ${ws.status === 'online' ? 'bg-green-400' : 'bg-gray-500'}`} />
                  <div className="flex-1 text-left min-w-0">
                    <div className="text-sm text-gray-200 truncate">{ws.name}</div>
                    <div className="text-xs text-gray-500 truncate">{ws.description}</div>
                  </div>
                  {activeWorkstation?.id === ws.id && (
                    <Check className="w-4 h-4 text-green-400 shrink-0" />
                  )}
                </button>
              ))}
            </div>
            {workstations.length === 0 && (
              <div className="p-4 text-center text-gray-500 text-sm">
                No agents registered
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default AgentSelector;
