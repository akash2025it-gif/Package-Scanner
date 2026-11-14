import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, ArrowRight, Lock, Mail, AlertCircle } from 'lucide-react';

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
    <div className="min-h-screen bg-[#f8f9ff] flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="w-14 h-14 rounded-2xl bg-[#0051d5] flex items-center justify-center shadow-lg">
            <ShieldAlert className="w-8 h-8 text-white" />
          </div>
        </div>
        <h2 className="mt-5 text-center font-display font-extrabold text-2xl text-gray-900 tracking-tight">
          PackCheck AI
        </h2>
        <p className="mt-1 text-center text-xs text-gray-500 font-medium">
          Legal Metrology (Packaged Commodities) Enforcement Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-6 shadow-xl shadow-blue-900/5 sm:rounded-2xl sm:px-10 border border-gray-200">
          <form className="space-y-4" onSubmit={handleSubmit}>
            {error && (
              <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-gray-700">Official Gov ID / Email</label>
              <div className="mt-1 relative rounded-xl shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="officer@packcheck.gov.in"
                  className="block w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700">Secure Passphrase</label>
              <div className="mt-1 relative rounded-xl shadow-xs">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="block w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-xl text-xs focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-xs font-bold text-white bg-[#0051d5] hover:bg-[#003ea7] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#0051d5] transition-all disabled:opacity-50"
              >
                {isLoading ? 'Authenticating Officer...' : 'Access Enforcement Terminal'}
                {!isLoading && <ArrowRight className="w-4 h-4" />}
              </button>
            </div>
          </form>

          {/* Quick Demo Fill Buttons */}
          <div className="mt-6 pt-5 border-t border-gray-100 text-xs">
            <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-2.5">
              Authorized Test Credentials
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setDemoRole('inspector.sharma@packcheck.gov.in', 'inspector123')}
                className="p-2 text-left rounded-lg bg-gray-50 border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition-colors"
              >
                <div className="font-bold text-gray-900 text-[11px]">Inspector</div>
                <div className="text-[10px] text-gray-500 truncate">V. Sharma (Delhi)</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoRole('admin@packcheck.gov.in', 'admin123')}
                className="p-2 text-left rounded-lg bg-gray-50 border border-gray-200 hover:bg-blue-50 hover:border-blue-300 transition-colors"
              >
                <div className="font-bold text-gray-900 text-[11px]">Administrator</div>
                <div className="text-[10px] text-gray-500 truncate">National HQ</div>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
