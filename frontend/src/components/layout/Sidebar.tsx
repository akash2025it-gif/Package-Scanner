import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  ScanLine,
  Clock,
  ClipboardCheck,
  FileText,
  BookOpen,
  BarChart3,
  Settings,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

export const Sidebar: React.FC<{ isOpen?: boolean; onClose?: () => void }> = ({ isOpen = false, onClose }) => {
  const { canScan } = useAuth();

  const links = [
    { to: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
    ...(canScan ? [{ to: '/scan/new', label: 'New Product Scan', icon: ScanLine, highlight: true }] : []),
    { to: '/review-queue', label: 'Review Queue', icon: ClipboardCheck },
    { to: '/history', label: 'Inspection History', icon: Clock },
    { to: '/reports', label: 'Compliance Reports', icon: FileText },
    { to: '/rules', label: 'Legal Rules & Slabs', icon: BookOpen },
    { to: '/analytics', label: 'Enforcement Analytics', icon: BarChart3 },
    { to: '/settings', label: 'Settings & Automation', icon: Settings },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-gradient-to-b from-[#001138] via-[#00174b] to-[#001b54] text-white select-none border-r border-white/5">
      {/* Brand Header */}
      <div className="p-5 flex items-center gap-3.5 border-b border-white/10">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#0051d5] to-[#276afa] flex items-center justify-center shadow-lg shadow-blue-500/20 ring-1 ring-white/20">
          <ShieldCheck className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-display font-black text-base tracking-tight text-white">PackCheck AI</span>
            <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-blue-500/20 text-blue-300 border border-blue-400/30">v2.4</span>
          </div>
          <span className="text-[10px] text-blue-300/80 font-semibold uppercase tracking-wider block">Legal Metrology</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={onClose}
              className={({ isActive }) =>
                `group relative flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                  isActive
                    ? 'bg-[#0051d5] text-white shadow-md shadow-blue-900/30 font-bold'
                    : 'text-slate-300 hover:text-white hover:bg-white/8'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-white rounded-r-full shadow-sm" />
                  )}
                  <Icon
                    className={`w-4 h-4 shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                      isActive ? 'text-white' : 'text-blue-300/70 group-hover:text-blue-200'
                    }`}
                  />
                  <span className="truncate">{link.label}</span>
                  {link.highlight && !isActive && (
                    <span className="ml-auto px-1.5 py-0.5 rounded text-[9px] font-bold bg-[#0051d5]/40 text-blue-200 border border-blue-400/20">
                      SCAN
                    </span>
                  )}
                </>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info Box */}
      <div className="p-4 border-t border-white/10 bg-black/20 text-[11px] text-blue-200/75">
        <div className="flex items-center gap-2 font-semibold text-white/90">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>Statutory LMPC 2011</span>
        </div>
        <p className="text-[10px] text-blue-300/70 mt-1 leading-snug">
          Rules 6(1)(a)-(k) • First Schedule font slabs • Metric SI compliance
        </p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop static sidebar */}
      <aside className="hidden md:block w-64 shrink-0 shadow-xl z-20">
        {sidebarContent}
      </aside>

      {/* Mobile drawer overlay */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/70 backdrop-blur-xs transition-opacity" onClick={onClose} />
          <div className="relative w-64 max-w-[80vw] h-full shadow-2xl z-10 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
