import React from 'react';
import { X, Volume2, VolumeX, History, Plus, Settings, LogOut, Shield } from 'lucide-react';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  audioEnabled: boolean;
  onToggleAudio: () => void;
  onShowHistory: () => void;
  onNewSession: () => void;
  onShowSettings: () => void;
  onLogout: () => void;
  onShowAdmin?: () => void;
  isAdmin?: boolean;
  userName?: string;
}

export const MobileMenu: React.FC<MobileMenuProps> = ({
  isOpen,
  onClose,
  audioEnabled,
  onToggleAudio,
  onShowHistory,
  onNewSession,
  onShowSettings,
  onLogout,
  onShowAdmin,
  isAdmin,
  userName,
}) => {
  if (!isOpen) return null;

  const menuItems = [
    {
      icon: audioEnabled ? Volume2 : VolumeX,
      label: audioEnabled ? 'Mute Audio' : 'Enable Audio',
      onClick: () => { onToggleAudio(); onClose(); },
      active: audioEnabled,
      activeColor: 'text-blue-400',
    },
    {
      icon: History,
      label: 'Session History',
      onClick: () => { onShowHistory(); onClose(); },
    },
    {
      icon: Plus,
      label: 'New Session',
      onClick: () => { onNewSession(); onClose(); },
      activeColor: 'text-green-400',
    },
    {
      icon: Settings,
      label: 'Settings',
      onClick: () => { onShowSettings(); onClose(); },
    },
  ];

  // Add admin panel if user is admin
  if (isAdmin && onShowAdmin) {
    menuItems.push({
      icon: Shield,
      label: 'Admin Panel',
      onClick: () => { onShowAdmin(); onClose(); },
      activeColor: 'text-purple-400',
    });
  }

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
        onClick={onClose}
      />
      
      {/* Menu Panel - slide from right */}
      <div className="fixed right-0 top-0 h-full w-64 bg-proxi-dark border-l border-gray-800 z-50 transform transition-transform">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <div>
            <div className="text-sm font-bold text-gray-200">Menu</div>
            {userName && (
              <div className="text-xs text-gray-500">{userName}</div>
            )}
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-gray-300 rounded-lg hover:bg-gray-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Menu Items */}
        <div className="p-2 space-y-1">
          {menuItems.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={item.onClick}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  item.active 
                    ? `${item.activeColor || 'text-proxi-accent'} bg-gray-800/50` 
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-sm">{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Logout - at bottom */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-800">
          <button
            onClick={() => { onLogout(); onClose(); }}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            <span className="text-sm">Logout</span>
          </button>
        </div>
      </div>
    </>
  );
};
