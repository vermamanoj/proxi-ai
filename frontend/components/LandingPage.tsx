import React, { useState } from 'react';
import { Zap, Play, Shield, CheckCircle2, Monitor, Terminal, Lock, Unlock, X, Loader2, Smartphone, ArrowRight, Eye, Brain, Wrench, FileText, Cloud, Send, HandMetal } from 'lucide-react';

interface LandingPageProps {
  onLogin: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLogin }) => {
  const [showWaitlist, setShowWaitlist] = useState(false);
  const [email, setEmail] = useState('');
  const [waitlistStatus, setWaitlistStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [waitlistMessage, setWaitlistMessage] = useState('');

  const handleWaitlistSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    
    setWaitlistStatus('loading');
    try {
      const response = await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });
      
      if (response.ok) {
        setWaitlistStatus('success');
        setWaitlistMessage('You\'re on the list! We\'ll be in touch.');
        setEmail('');
      } else {
        const data = await response.json();
        setWaitlistStatus('error');
        setWaitlistMessage(data.detail || 'Something went wrong. Please try again.');
      }
    } catch {
      setWaitlistStatus('error');
      setWaitlistMessage('Connection error. Please try again.');
    }
  };

  return (
    <div className="h-screen bg-black text-white overflow-y-scroll">
      {/* Navigation - Sticky */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-black/90 backdrop-blur-lg border-b border-gray-800/50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-proxi-accent" />
            <span className="text-lg font-bold tracking-tight">PROXI</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={onLogin}
              className="px-3 py-1.5 text-sm text-gray-300 hover:text-white transition-colors"
            >
              Login
            </button>
            <button
              onClick={() => setShowWaitlist(true)}
              className="px-3 py-1.5 text-sm bg-proxi-accent text-black font-medium rounded-lg hover:bg-proxi-accent/90 transition-colors"
            >
              Join Waitlist
            </button>
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section className="pt-24 pb-16 sm:pt-32 sm:pb-24 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-proxi-accent/10 border border-proxi-accent/30 rounded-full text-proxi-accent text-xs sm:text-sm mb-6">
            <Zap className="w-3 h-3 sm:w-4 sm:h-4" />
            <span>Google Gemini Hackathon 2026</span>
          </div>
          
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold mb-4 leading-tight tracking-tight">
            Verified Execution for Real Computers.
          </h1>
          
          <p className="text-lg sm:text-xl text-gray-300 max-w-2xl mx-auto mb-3">
            Proxi executes real work on real systems — safely, verifiably, and under human control.
          </p>
          
          <p className="text-base text-gray-500 max-w-xl mx-auto mb-8">
            When APIs don't exist and trust still matters.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
            <button
              onClick={onLogin}
              className="w-full sm:w-auto px-6 py-3 bg-proxi-accent text-black font-semibold rounded-xl hover:bg-proxi-accent/90 transition-all flex items-center justify-center gap-2"
            >
              Login
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setShowWaitlist(true)}
              className="w-full sm:w-auto px-6 py-3 bg-gray-800 text-white font-semibold rounded-xl hover:bg-gray-700 transition-all flex items-center justify-center gap-2"
            >
              Join Waitlist
            </button>
          </div>
        </div>
      </section>

      {/* PROBLEM SECTION */}
      <section className="py-12 sm:py-16 px-4 sm:px-6 border-t border-gray-800/50">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-xl sm:text-2xl text-gray-300 font-light">
            AI can reason. <span className="text-gray-500">Execution still happens behind keyboards.</span>
          </p>
        </div>
      </section>

      {/* SOLUTION SECTION */}
      <section className="py-12 sm:py-16 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-gray-900 to-black rounded-2xl border border-gray-800 p-6 sm:p-10">
            <div className="flex flex-col md:flex-row items-center gap-6 md:gap-10">
              <div className="flex-shrink-0">
                <div className="w-20 h-20 sm:w-24 sm:h-24 bg-proxi-accent/10 rounded-2xl flex items-center justify-center">
                  <Smartphone className="w-10 h-10 sm:w-12 sm:h-12 text-proxi-accent" />
                </div>
              </div>
              <div className="text-center md:text-left">
                <h2 className="text-2xl sm:text-3xl font-bold mb-3">
                  Proxi executes verified actions on real computers — even when you're away from the keyboard.
                </h2>
                <p className="text-gray-400">
                  Navigates real desktop apps, browsers, and terminals — including legacy systems without APIs.
                  Executes multi-step workflows end-to-end.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* TRUST BY DESIGN SECTION */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 bg-gray-900/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-3">
            Trust by Design
          </h2>
          <p className="text-gray-400 text-center mb-10 sm:mb-12">
            Most agents claim success. Proxi proves it.
          </p>

          <div className="grid md:grid-cols-2 gap-6 sm:gap-8">
            {/* Verified Execution */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-semibold">Verified Execution</h3>
              </div>
              <ul className="space-y-3 text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-green-400 mt-1">•</span>
                  Screenshots as evidence
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-400 mt-1">•</span>
                  Visual confirmation sent to your phone
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-green-400 mt-1">•</span>
                  No "agent said it worked"
                </li>
              </ul>
            </div>

            {/* Safety & Control */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                  <Shield className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="text-lg sm:text-xl font-semibold">Safety & Control</h3>
              </div>
              <div className="space-y-3 text-gray-400">
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 bg-green-500 rounded-full"></span>
                  <span>Safe — auto-allowed</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 bg-yellow-500 rounded-full"></span>
                  <span>Sensitive — human approval required</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="w-3 h-3 bg-red-500 rounded-full"></span>
                  <span>Blocked — never executed</span>
                </div>
              </div>
            </div>
          </div>

          <p className="text-center text-lg sm:text-xl text-gray-300 mt-10 sm:mt-12 font-light italic">
            "Proxi never decides success. Reality does."
          </p>
        </div>
      </section>

      {/* POWERED BY GEMINI */}
      <section id="demo" className="py-16 sm:py-20 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 border border-blue-500/30 rounded-full text-blue-400 text-xs mb-4">
            <span>Powered by Gemini 3</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold mb-3">
            Why Gemini Changes Everything
          </h2>
          <p className="text-gray-400 mb-8 max-w-2xl">
            No hardcoded scripts. No brittle selectors. Proxi reasons through what it sees.
          </p>

          <div className="grid sm:grid-cols-2 gap-4 sm:gap-6">
            {/* Multimodal Vision */}
            <div className="bg-gradient-to-br from-blue-900/20 to-gray-900/50 rounded-2xl border border-blue-800/30 p-5 sm:p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-blue-500/10 rounded-xl flex items-center justify-center">
                  <Eye className="w-5 h-5 text-blue-400" />
                </div>
                <h3 className="font-semibold">Multimodal Vision</h3>
              </div>
              <p className="text-gray-400 text-sm">
                Reads live screenshots like a human — understands UI layout, text, error messages, and context without hardcoded selectors.
              </p>
            </div>

            {/* Native Reasoning */}
            <div className="bg-gradient-to-br from-purple-900/20 to-gray-900/50 rounded-2xl border border-purple-800/30 p-5 sm:p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-purple-500/10 rounded-xl flex items-center justify-center">
                  <Brain className="w-5 h-5 text-purple-400" />
                </div>
                <h3 className="font-semibold">On-the-Fly Reasoning</h3>
              </div>
              <p className="text-gray-400 text-sm">
                Decides next action based on visual feedback. Adapts when buttons move, dialogs appear, or errors happen unexpectedly.
              </p>
            </div>

            {/* Native Tool Use */}
            <div className="bg-gradient-to-br from-green-900/20 to-gray-900/50 rounded-2xl border border-green-800/30 p-5 sm:p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-green-500/10 rounded-xl flex items-center justify-center">
                  <Wrench className="w-5 h-5 text-green-400" />
                </div>
                <h3 className="font-semibold">Native Function Calling</h3>
              </div>
              <p className="text-gray-400 text-sm">
                Executes desktop tools directly via Gemini's native tool-use. No LangChain wrappers, no prompt hacks — just clean execution.
              </p>
            </div>

            {/* Long Context */}
            <div className="bg-gradient-to-br from-orange-900/20 to-gray-900/50 rounded-2xl border border-orange-800/30 p-5 sm:p-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 bg-orange-500/10 rounded-xl flex items-center justify-center">
                  <FileText className="w-5 h-5 text-orange-400" />
                </div>
                <h3 className="font-semibold">Long Context Memory</h3>
              </div>
              <p className="text-gray-400 text-sm">
                Maintains full workflow history across complex multi-step tasks. Picks up where it left off, remembers what it saw.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-16 sm:py-20 px-4 sm:px-6 bg-gray-900/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-3">
            How It Works
          </h2>
          <p className="text-gray-400 text-center mb-10 sm:mb-12">
            Command from your phone. Execute on your desktop. Stay in control.
          </p>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {/* Step 1: Command */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-5 text-center">
              <div className="w-12 h-12 bg-proxi-accent/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Smartphone className="w-6 h-6 text-proxi-accent" />
              </div>
              <h3 className="font-semibold mb-2">Command</h3>
              <p className="text-gray-400 text-sm">
                Send natural language requests from your phone — anywhere, anytime.
              </p>
            </div>

            {/* Step 2: Execute */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-5 text-center">
              <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Monitor className="w-6 h-6 text-blue-400" />
              </div>
              <h3 className="font-semibold mb-2">Execute</h3>
              <p className="text-gray-400 text-sm">
                Proxi agent controls your desktop — apps, browsers, terminals, legacy systems.
              </p>
            </div>

            {/* Step 3: Approve */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-5 text-center">
              <div className="w-12 h-12 bg-yellow-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                <HandMetal className="w-6 h-6 text-yellow-400" />
              </div>
              <h3 className="font-semibold mb-2">Approve</h3>
              <p className="text-gray-400 text-sm">
                Sensitive actions pause for your approval. Dangerous commands are blocked.
              </p>
            </div>

            {/* Step 4: Verify */}
            <div className="bg-black/50 rounded-2xl border border-gray-800 p-5 text-center">
              <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="font-semibold mb-2">Verify</h3>
              <p className="text-gray-400 text-sm">
                Screenshots and files sent back to your phone as proof of completion.
              </p>
            </div>
          </div>

          {/* Mobile-first callout */}
          <div className="mt-8 bg-gradient-to-r from-proxi-accent/10 to-transparent rounded-xl border border-proxi-accent/20 p-4 sm:p-6 flex flex-col sm:flex-row items-center gap-4">
            <Send className="w-8 h-8 text-proxi-accent shrink-0" />
            <div>
              <p className="text-gray-300 font-medium">Share files both ways</p>
              <p className="text-gray-500 text-sm">Send screenshots from your phone to the desktop. Receive results, exports, and confirmations back.</p>
            </div>
          </div>
        </div>
      </section>

      {/* OS-AWARE EXECUTION */}
      <section className="py-16 sm:py-20 px-4 sm:px-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold text-center mb-3">
            OS-Aware Intelligence
          </h2>
          <p className="text-gray-400 text-center mb-10 sm:mb-12">
            Proxi understands the state of your machine.
          </p>

          <div className="grid md:grid-cols-2 gap-6">
            {/* Unlocked */}
            <div className="bg-black/50 rounded-2xl border border-green-800/30 p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-4">
                <Unlock className="w-6 h-6 text-green-400" />
                <h3 className="font-semibold">Desktop Unlocked</h3>
              </div>
              <div className="flex items-center gap-3 mb-4">
                <Monitor className="w-12 h-12 text-green-400/50" />
                <div>
                  <p className="text-gray-300">Full UI control</p>
                  <p className="text-gray-500 text-sm">Mouse, keyboard, apps</p>
                </div>
              </div>
            </div>

            {/* Locked */}
            <div className="bg-black/50 rounded-2xl border border-yellow-800/30 p-6 sm:p-8">
              <div className="flex items-center gap-3 mb-4">
                <Lock className="w-6 h-6 text-yellow-400" />
                <h3 className="font-semibold">Desktop Locked</h3>
              </div>
              <div className="flex items-center gap-3 mb-4">
                <Terminal className="w-12 h-12 text-yellow-400/50" />
                <div>
                  <p className="text-gray-300">Terminal fallback</p>
                  <p className="text-gray-500 text-sm">Commands still work</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* INSPIRATION STORY */}
      <section className="py-16 sm:py-20 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl font-bold mb-6">
            Built for Real Moments
          </h2>
          <p className="text-lg text-gray-400 leading-relaxed">
            The idea came from real moments — like negotiating pricing in a meeting without a laptop,
            knowing the data was sitting on a computer back at the office.
          </p>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="py-8 sm:py-10 px-4 sm:px-6 border-t border-gray-800">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-proxi-accent" />
              <span className="font-bold">PROXI</span>
            </div>
            <p className="text-gray-500 text-sm text-center">
              Supports Windows and Linux systems deployed on your infrastructure.
            </p>
            <p className="text-gray-600 text-xs">
              Built for real-world constraints.
            </p>
          </div>
        </div>
      </footer>

      {/* WAITLIST MODAL */}
      {showWaitlist && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-gray-900 rounded-2xl border border-gray-800 p-6 sm:p-8 w-full max-w-md relative">
            <button
              onClick={() => { setShowWaitlist(false); setWaitlistStatus('idle'); }}
              className="absolute top-4 right-4 text-gray-500 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="text-center mb-6">
              <Zap className="w-10 h-10 text-proxi-accent mx-auto mb-3" />
              <h3 className="text-xl font-bold">Join the Waitlist</h3>
              <p className="text-gray-400 text-sm mt-1">Be first to try Proxi when it launches.</p>
            </div>

            {waitlistStatus === 'success' ? (
              <div className="text-center py-4">
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3" />
                <p className="text-green-400">{waitlistMessage}</p>
              </div>
            ) : (
              <form onSubmit={handleWaitlistSubmit} className="space-y-4">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="your@email.com"
                  required
                  className="w-full px-4 py-3 bg-black border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-proxi-accent"
                />
                {waitlistStatus === 'error' && (
                  <p className="text-red-400 text-sm">{waitlistMessage}</p>
                )}
                <button
                  type="submit"
                  disabled={waitlistStatus === 'loading'}
                  className="w-full py-3 bg-proxi-accent text-black font-semibold rounded-xl hover:bg-proxi-accent/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {waitlistStatus === 'loading' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Joining...
                    </>
                  ) : (
                    'Join Waitlist'
                  )}
                </button>
              </form>
            )}

            <p className="text-gray-500 text-xs text-center mt-4">
              Already have access? <button onClick={onLogin} className="text-proxi-accent hover:underline">Login</button>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
