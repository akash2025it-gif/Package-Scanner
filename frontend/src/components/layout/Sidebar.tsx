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
  ShieldAlert,
} from 'lucide-react';

export const Sidebar: React.FC<{ isOpen?: boolean; onClose?: () => void }> = ({ isOpen = false, onClose }) => {
  const { canScan, isAdmin } = useAuth();

  const links = [
    { to: '/', label: 'Overview Dashboard', icon: LayoutDashboard },
    ...(canScan ? [{ to: '/scan/new', label: 'New Product Scan', icon: ScanLine }] : []),
    { to: '/review-queue', label: 'Review Queue', icon: ClipboardCheck },
    { to: '/history', label: 'Inspection History', icon: Clock },
    { to: '/reports', label: 'Compliance Reports', icon: FileText },
    { to: '/rules', label: 'Legal Rules & Slabs', icon: BookOpen },
    { to: '/analytics', label: 'Enforcement Analytics', icon: BarChart3 },
    { to: '/settings', label: 'Settings & Automation', icon: Settings },
  ];

  const sidebarContent = (
    <div className="flex flex-col h-full bg-[#00174b] text-white select-none">
      <div className="p-5 flex items-center gap-3 border-b border-white/10">
        <div className="w-10 h-10 rounded-xl bg-[#0051d5] flex items-center justify-center shadow-md">
          <ShieldAlert className="w-6 h-6 text-white" />
        </div>
        <div>
          <span className="font-display font-extrabold text-base tracking-tight block">PackCheck AI</span>
          <span className="text-[10px] text-blue-300 font-semibold uppercase tracking-wider block">Legal Metrology</span>
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-[#0051d5] text-white shadow-sm'
                    : 'text-blue-100 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/10 text-[11px] text-blue-200/80 bg-black/15">
        <p className="font-semibold text-white/90">LMPC Rules, 2011</p>
        <p className="text-[10px] text-blue-300 mt-0.5">Statutory Verification Engine v2.4</p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop static sidebar */}
      <aside className="hidden md:block w-64 shrink-0 shadow-lg z-20">
        {sidebarContent}
      </aside>

      {/* Mobile drawer overlay */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/60 backdrop-blur-xs" onClick={onClose} />
          <div className="relative w-64 max-w-[80vw] h-full shadow-2xl z-10">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
