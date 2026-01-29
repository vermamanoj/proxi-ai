import React, { useState } from 'react';
import { Zap, Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react';

interface LoginPageProps {
  onLogin: (username: string, password: string, rememberMe?: boolean) => Promise<boolean>;
  onBack?: () => void;  // Optional - hidden on mobile app
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onBack }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const success = await onLogin(username, password, rememberMe);
      if (!success) {
        setError('Invalid username or password');
      }
    } catch (err) {
      setError('Connection error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center px-6">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          {onBack ? (
            <button 
              onClick={onBack}
              className="inline-flex items-center gap-2 mb-6 hover:opacity-80 transition-opacity"
            >
              <Zap className="w-10 h-10 text-proxi-accent" />
              <span className="text-2xl font-bold">PROXI</span>
            </button>
          ) : (
            <div className="inline-flex items-center gap-2 mb-6">
              <Zap className="w-10 h-10 text-proxi-accent" />
              <span className="text-2xl font-bold">PROXI</span>
            </div>
          )}
          <h1 className="text-2xl font-semibold">Welcome back</h1>
          <p className="text-gray-400 mt-2">Sign in to access your workstations</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3 text-red-400">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Username Field */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-gray-900 border border-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-proxi-accent/50 transition-colors"
              placeholder="Enter your username"
              required
              autoComplete="username"
              autoFocus
            />
          </div>

          {/* Password Field */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 bg-gray-900 border border-gray-800 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-proxi-accent/50 transition-colors pr-12"
                placeholder="Enter your password"
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Remember Me */}
          <div className="flex items-center">
            <input
              id="remember-me"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 bg-gray-900 text-proxi-accent focus:ring-proxi-accent/50"
            />
            <label htmlFor="remember-me" className="ml-2 text-sm text-gray-400">
              Remember me for 24 hours
            </label>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || !username || !password}
            className="w-full py-3 bg-proxi-accent text-black font-semibold rounded-xl hover:bg-proxi-accent/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </button>
        </form>

        
        {/* Footer */}
        <p className="text-center text-gray-500 text-sm mt-8">
          Built for Google Gemini Hackathon 2026
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
