import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { ShieldCheck, LogOut, User as UserIcon, Bell } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Navbar: React.FC<{ onMenuToggle?: () => void }> = ({ onMenuToggle }) => {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {onMenuToggle && (
            <button
              onClick={onMenuToggle}
              className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100"
              aria-label="Toggle menu"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              Legal Metrology Division • Govt. of India
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="hidden sm:inline">Engine Online (LMPC 2011)</span>
          </div>

          {user && (
            <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
              <Link to="/settings" className="flex items-center gap-2 hover:opacity-85 transition-opacity">
                <div className="w-8 h-8 rounded-full bg-[#0051d5] text-white flex items-center justify-center font-bold text-xs">
                  {user.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()}
                </div>
                <div className="hidden md:block text-left">
                  <div className="text-xs font-bold text-gray-900 leading-tight">{user.name}</div>
                  <div className="text-[10px] text-gray-500 capitalize">{user.role} • {user.region || 'National'}</div>
                </div>
              </Link>

              <button
                onClick={logout}
                title="Sign out"
                className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
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
