import React from 'react';
import { Zap, Monitor, Smartphone, Shield, ArrowRight, Github, Play } from 'lucide-react';

interface LandingPageProps {
  onLogin: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLogin }) => {
  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-lg border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-8 h-8 text-proxi-accent" />
            <span className="text-xl font-bold">PROXI</span>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={onLogin}
              className="px-4 py-2 bg-proxi-accent text-black font-medium rounded-lg hover:bg-proxi-accent/90 transition-colors"
            >
              Login
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-6">
        <div className="max-w-6xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-proxi-accent/10 border border-proxi-accent/30 rounded-full text-proxi-accent text-sm mb-6">
            <Zap className="w-4 h-4" />
            <span>Google Gemini Hackathon 2026</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold mb-6 leading-tight">
            Your AI Desktop Agent
            <br />
            <span className="text-proxi-accent">Anywhere You Go</span>
          </h1>
          
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10">
            Control your Windows or Linux desktop from your phone using voice commands. 
            Proxi sees your screen, understands context, and executes tasks with full transparency.
          </p>

          <div className="flex items-center justify-center gap-4">
            <button
              onClick={onLogin}
              className="px-8 py-4 bg-proxi-accent text-black font-semibold rounded-xl hover:bg-proxi-accent/90 transition-all flex items-center gap-2 text-lg"
            >
              Get Started
              <ArrowRight className="w-5 h-5" />
            </button>
            <a
              href="#demo"
              className="px-8 py-4 bg-gray-800 text-white font-semibold rounded-xl hover:bg-gray-700 transition-all flex items-center gap-2 text-lg"
            >
              <Play className="w-5 h-5" />
              Watch Demo
            </a>
          </div>
        </div>
      </section>

      {/* Demo Video Section */}
      <section id="demo" className="py-20 px-6 bg-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <div className="aspect-video bg-gray-800 rounded-2xl border border-gray-700 flex items-center justify-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-proxi-accent/20 to-transparent" />
            <div className="text-center z-10">
              <Play className="w-16 h-16 text-proxi-accent mx-auto mb-4" />
              <p className="text-gray-400">Demo Video Coming Soon</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            How Proxi Works
          </h2>
          <p className="text-gray-400 text-center max-w-2xl mx-auto mb-16">
            A transparent AI agent that bridges your mobile device with your desktop workstation
          </p>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-proxi-accent/50 transition-colors">
              <div className="w-14 h-14 bg-proxi-accent/10 rounded-xl flex items-center justify-center mb-6">
                <Smartphone className="w-7 h-7 text-proxi-accent" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Voice Commands</h3>
              <p className="text-gray-400">
                Speak naturally to your phone. Proxi understands context and intent, 
                translating your requests into precise desktop actions.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-proxi-accent/50 transition-colors">
              <div className="w-14 h-14 bg-proxi-accent/10 rounded-xl flex items-center justify-center mb-6">
                <Monitor className="w-7 h-7 text-proxi-accent" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Desktop Automation</h3>
              <p className="text-gray-400">
                Full OS-level control including mouse, keyboard, file operations, 
                and application automation. Works with legacy apps too.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-8 bg-gray-900 rounded-2xl border border-gray-800 hover:border-proxi-accent/50 transition-colors">
              <div className="w-14 h-14 bg-proxi-accent/10 rounded-xl flex items-center justify-center mb-6">
                <Shield className="w-7 h-7 text-proxi-accent" />
              </div>
              <h3 className="text-xl font-semibold mb-3">Human-in-the-Loop</h3>
              <p className="text-gray-400">
                Every action requires your approval. Command guardrails prevent 
                dangerous operations. Full transparency with real-time traces.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="py-20 px-6 bg-gray-900/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center mb-4">
            Enterprise-Ready Architecture
          </h2>
          <p className="text-gray-400 text-center max-w-2xl mx-auto mb-16">
            Multi-workstation support with secure connectivity
          </p>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Workstation Card - Linux */}
            <div className="p-6 bg-black rounded-2xl border border-gray-800">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
                <h3 className="font-semibold">Linux Container</h3>
                <span className="text-xs text-gray-500 ml-auto">Always Online</span>
              </div>
              <p className="text-gray-400 text-sm mb-4">
                Ubuntu Docker container for terminal automation, git, python, and DevOps tasks.
              </p>
              <div className="flex flex-wrap gap-2">
                {['Terminal', 'Git', 'Python', 'Docker'].map(cap => (
                  <span key={cap} className="px-2 py-1 bg-gray-800 text-gray-400 text-xs rounded">
                    {cap}
                  </span>
                ))}
              </div>
            </div>

            {/* Workstation Card - Windows */}
            <div className="p-6 bg-black rounded-2xl border border-gray-800">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-3 h-3 bg-blue-500 rounded-full" />
                <h3 className="font-semibold">Windows Server</h3>
                <span className="text-xs text-gray-500 ml-auto">On-Demand</span>
              </div>
              <p className="text-gray-400 text-sm mb-4">
                Windows Server 2022 with GUI automation, Office apps, and legacy enterprise tools.
              </p>
              <div className="flex flex-wrap gap-2">
                {['Desktop', 'PowerPoint', 'CRM', 'Browser'].map(cap => (
                  <span key={cap} className="px-2 py-1 bg-gray-800 text-gray-400 text-xs rounded">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to Work Smarter?
          </h2>
          <p className="text-gray-400 text-lg mb-10">
            Experience the future of remote desktop automation with AI-powered assistance.
          </p>
          <button
            onClick={onLogin}
            className="px-10 py-4 bg-proxi-accent text-black font-semibold rounded-xl hover:bg-proxi-accent/90 transition-all text-lg"
          >
            Login to Proxi
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-gray-800">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-proxi-accent" />
            <span className="text-sm text-gray-400">PROXI © 2026</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
