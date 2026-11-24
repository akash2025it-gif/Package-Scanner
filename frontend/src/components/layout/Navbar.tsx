import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { ShieldCheck, LogOut, Search, Bell, Sparkles, Activity } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

export const Navbar: React.FC<{ onMenuToggle?: () => void }> = ({ onMenuToggle }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [searchVal, setSearchVal] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchVal.trim()) {
      navigate(`/history?q=${encodeURIComponent(searchVal.trim())}`);
    }
  };

  return (
    <header className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-30 transition-all">
      <div className="px-4 sm:px-6 lg:px-8 py-2.5 flex items-center justify-between gap-4">
        {/* Left: Mobile trigger & Division Badge */}
        <div className="flex items-center gap-3">
          {onMenuToggle && (
            <button
              onClick={onMenuToggle}
              className="md:hidden p-2 rounded-xl text-slate-600 hover:bg-slate-100 focus:outline-none transition-colors"
              aria-label="Toggle menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold bg-gradient-to-r from-blue-50 to-indigo-50 text-[#0051d5] border border-blue-200/70 shadow-2xs">
              <span className="w-1.5 h-1.5 rounded-full bg-[#0051d5]"></span>
              Legal Metrology Division • Govt. of India
            </span>
          </div>
        </div>

        {/* Center: Global Quick Search */}
        <div className="hidden lg:flex items-center flex-1 max-w-md mx-4">
          <form onSubmit={handleSearchSubmit} className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchVal}
              onChange={(e) => setSearchVal(e.target.value)}
              placeholder="Search inspections by commodity, batch, or ID..."
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:border-[#0051d5] focus:outline-none transition-all placeholder:text-slate-400"
            />
          </form>
        </div>

        {/* Right: Engine Telemetry & Officer Profile */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Live Engine Status */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-emerald-50/80 border border-emerald-200/60 text-[11px] font-medium text-emerald-800">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="hidden md:inline font-mono font-semibold">LMPC 2011 Engine Active</span>
            <span className="md:hidden">Live</span>
          </div>

          {user && (
            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
              <Link
                to="/settings"
                className="flex items-center gap-2.5 p-1 rounded-xl hover:bg-slate-50 transition-colors group"
                title="View officer profile and settings"
              >
                <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#00174b] to-[#0051d5] text-white flex items-center justify-center font-bold text-xs shadow-xs group-hover:scale-105 transition-transform">
                  {user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
                </div>
                <div className="hidden sm:block text-left">
                  <div className="text-xs font-bold text-slate-800 leading-tight group-hover:text-[#0051d5] transition-colors">
                    {user.name}
                  </div>
                  <div className="text-[10px] text-slate-500 font-medium capitalize">
                    {user.role} • {user.region || 'National'}
                  </div>
                </div>
              </Link>

              <button
                onClick={logout}
                title="Sign out of inspector session"
                className="p-2 rounded-xl text-slate-400 hover:text-red-600 hover:bg-red-50 focus:outline-none transition-all"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
