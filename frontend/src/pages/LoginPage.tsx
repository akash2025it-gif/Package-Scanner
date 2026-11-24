import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, ArrowRight, Lock, Mail, AlertCircle, Sparkles, CheckCircle2 } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('inspector.sharma@packcheck.gov.in');
  const [password, setPassword] = useState('inspector123');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await login(email, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const setDemoRole = (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#001138] via-[#00174b] to-[#00287a] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 select-none">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-[#0051d5] to-[#276afa] flex items-center justify-center shadow-xl shadow-blue-500/30 ring-1 ring-white/20">
            <ShieldCheck className="w-9 h-9 text-white" />
          </div>
        </div>
        <div className="text-center mt-5">
          <span className="px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-widest bg-white/10 text-blue-200 border border-white/15">
            Legal Metrology Division
          </span>
          <h1 className="mt-2 text-center font-display font-black text-2xl sm:text-3xl text-white tracking-tight">
            PackCheck AI
          </h1>
          <p className="mt-1 text-center text-xs text-blue-200/80 font-medium">
            Packaged Commodities Compliance Inspection Platform (LMPC 2011)
          </p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white/95 backdrop-blur-md py-8 px-6 shadow-2xl rounded-3xl sm:px-10 border border-white/20 space-y-5">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3.5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5 shadow-2xs">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                <span className="font-semibold">{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-bold text-slate-700">Official Officer ID / Email</label>
              <div className="mt-1 relative rounded-xl shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@packcheck.gov.in"
                  className="block w-full pl-9 pr-3.5 py-2.5 border border-slate-300 rounded-xl text-xs bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:border-[#0051d5] focus:outline-none transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700">Inspection Passphrase</label>
              <div className="mt-1 relative rounded-xl shadow-2xs">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-9 pr-3.5 py-2.5 border border-slate-300 rounded-xl text-xs bg-slate-50/50 focus:bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:border-[#0051d5] focus:outline-none transition-all"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-2xl shadow-md shadow-blue-900/20 text-xs font-bold text-white bg-[#0051d5] hover:bg-[#003ea7] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0051d5] transition-all disabled:opacity-50 cursor-pointer"
              >
                {isLoading ? 'Authenticating Officer...' : 'Access Enforcement Terminal'}
                {!isLoading && <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          </form>

          {/* Quick Demo Fill Buttons */}
          <div className="pt-4 border-t border-slate-100 text-xs space-y-2">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider block">
              1-Click Demo Credentials
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setDemoRole('inspector.sharma@packcheck.gov.in', 'inspector123')}
                className="p-2.5 text-left rounded-xl bg-slate-50 border border-slate-200 hover:bg-blue-50 hover:border-blue-300 transition-all cursor-pointer group"
              >
                <div className="font-bold text-slate-900 text-[11px] group-hover:text-[#0051d5]">Inspector</div>
                <div className="text-[10px] text-slate-500 truncate">V. Sharma (Delhi)</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('admin@packcheck.gov.in', 'admin123')}
                className="p-2.5 text-left rounded-xl bg-slate-50 border border-slate-200 hover:bg-blue-50 hover:border-blue-300 transition-all cursor-pointer group"
              >
                <div className="font-bold text-slate-900 text-[11px] group-hover:text-[#0051d5]">Administrator</div>
                <div className="text-[10px] text-slate-500 truncate">National HQ</div>
              </button>
            </div>
          </div>
        </div>

        <div className="mt-6 text-center text-[10px] text-blue-200/60">
          Authorized Legal Metrology Officers • Section 15 Enforcement Platform
        </div>
      </div>
    </div>
  );
};
