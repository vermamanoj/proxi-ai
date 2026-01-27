import React, { useState, useEffect } from 'react';
import { Link2, Copy, Trash2, Plus, Clock, Users, Shield, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { API_BASE } from '../constants';

interface MagicLink {
  token: string;
  label: string;
  role: string;
  uses_remaining: number;
  expires_at: string;
  is_valid: boolean;
  created_at: string;
}

interface AdminPanelProps {
  onClose: () => void;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({ onClose }) => {
  const [links, setLinks] = useState<MagicLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);
  
  // Form state
  const [newLink, setNewLink] = useState({
    role: 'judge',
    label: 'Hackathon Judge',
    expires_hours: 168,
    uses: 50
  });

  useEffect(() => {
    fetchLinks();
  }, []);

  const fetchLinks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/magic-links`, {
        credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setLinks(data.links || []);
        setError(null);
      } else if (res.status === 403) {
        setError('Admin access required');
      } else {
        setError('Failed to load magic links');
      }
    } catch (e) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const createLink = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/auth/magic-link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newLink)
      });
      
      if (res.ok) {
        setShowCreateForm(false);
        fetchLinks();
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to create link');
      }
    } catch (e) {
      setError('Failed to create link');
    }
  };

  const revokeLink = async (token: string) => {
    if (!confirm('Revoke this magic link? Judges using it will lose access.')) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/auth/magic-link/${token}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (res.ok) {
        fetchLinks();
      }
    } catch (e) {
      setError('Failed to revoke link');
    }
  };

  const copyLink = (token: string) => {
    const url = `${window.location.origin}?magic=${token}`;
    navigator.clipboard.writeText(url);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const formatDate = (isoDate: string) => {
    const date = new Date(isoDate);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTimeRemaining = (expiresAt: string) => {
    const now = new Date();
    const expires = new Date(expiresAt);
    const hours = Math.floor((expires.getTime() - now.getTime()) / (1000 * 60 * 60));
    if (hours < 0) return 'Expired';
    if (hours < 24) return `${hours}h left`;
    return `${Math.floor(hours / 24)}d left`;
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 rounded-lg w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-proxi-accent" />
            <h2 className="text-lg font-bold">Admin Panel</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-800 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <span className="text-red-400 text-sm">{error}</span>
              <button onClick={() => setError(null)} className="ml-auto">
                <X className="w-4 h-4 text-red-400" />
              </button>
            </div>
          )}

          {/* Magic Links Section */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Magic Links
              </h3>
              <button
                onClick={() => setShowCreateForm(true)}
                className="flex items-center gap-1 px-3 py-1.5 bg-proxi-accent text-black rounded text-sm font-medium hover:bg-proxi-accent/90"
              >
                <Plus className="w-4 h-4" />
                New Link
              </button>
            </div>

            {/* Create Form */}
            {showCreateForm && (
              <div className="mb-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
                <h4 className="text-sm font-semibold mb-3">Create Magic Link</h4>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Label</label>
                    <input
                      type="text"
                      value={newLink.label}
                      onChange={(e) => setNewLink({ ...newLink, label: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm"
                      placeholder="e.g., Hackathon Judge"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Role</label>
                    <select
                      value={newLink.role}
                      onChange={(e) => setNewLink({ ...newLink, role: e.target.value })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm"
                    >
                      <option value="user">User</option>
                      <option value="judge">Judge</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Expires (hours)</label>
                    <input
                      type="number"
                      value={newLink.expires_hours}
                      onChange={(e) => setNewLink({ ...newLink, expires_hours: parseInt(e.target.value) || 72 })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm"
                      min={1}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Max Uses</label>
                    <input
                      type="number"
                      value={newLink.uses}
                      onChange={(e) => setNewLink({ ...newLink, uses: parseInt(e.target.value) || 10 })}
                      className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded text-sm"
                      min={1}
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setShowCreateForm(false)}
                    className="px-3 py-1.5 text-sm text-gray-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={createLink}
                    className="px-3 py-1.5 bg-proxi-accent text-black rounded text-sm font-medium hover:bg-proxi-accent/90"
                  >
                    Create Link
                  </button>
                </div>
              </div>
            )}

            {/* Links List */}
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : links.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Link2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No magic links created yet</p>
                <p className="text-xs mt-1">Create one to share with hackathon judges</p>
              </div>
            ) : (
              <div className="space-y-2">
                {links.map((link) => (
                  <div
                    key={link.token}
                    className={`p-3 rounded-lg border ${
                      link.is_valid 
                        ? 'bg-gray-800/50 border-gray-700' 
                        : 'bg-gray-800/30 border-gray-800 opacity-60'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium truncate">{link.label || 'Unnamed Link'}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            link.role === 'admin' ? 'bg-red-500/20 text-red-400' :
                            link.role === 'judge' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-gray-500/20 text-gray-400'
                          }`}>
                            {link.role}
                          </span>
                          {link.is_valid ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                          ) : (
                            <AlertCircle className="w-3.5 h-3.5 text-red-500" />
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Users className="w-3 h-3" />
                            {link.uses_remaining} uses left
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {getTimeRemaining(link.expires_at)}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => copyLink(link.token)}
                          className={`p-1.5 rounded hover:bg-gray-700 ${
                            copiedToken === link.token ? 'text-green-400' : 'text-gray-400'
                          }`}
                          title="Copy link"
                        >
                          {copiedToken === link.token ? (
                            <CheckCircle2 className="w-4 h-4" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => revokeLink(link.token)}
                          className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-red-400"
                          title="Revoke link"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Reference */}
          <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Quick Reference</h4>
            <div className="text-xs text-gray-500 space-y-1">
              <p><strong className="text-gray-400">Hackathon Duration:</strong> Feb 10-27, 2026 (17 days = 408 hours)</p>
              <p><strong className="text-gray-400">Recommended:</strong> 168h expiry, 50 uses for judges</p>
              <p><strong className="text-gray-400">Link Format:</strong> {window.location.origin}?magic=TOKEN</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
