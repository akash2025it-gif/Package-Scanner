import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#f8f9ff] text-slate-800 overflow-hidden font-sans">
      <Sidebar isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Navbar onMenuToggle={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
          <div className="max-w-7xl mx-auto w-full">
            <Outlet />
          </div>
          <footer className="mt-12 pt-5 pb-3 border-t border-slate-200/80 text-[11px] text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-3 max-w-7xl mx-auto w-full">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-[#00174b]">PackCheck AI</span>
              <span className="text-slate-300">•</span>
              <span>Legal Metrology (Packaged Commodities) Rules, 2011</span>
            </div>
            <div className="text-[10px] text-slate-400 text-center sm:text-right max-w-xl leading-relaxed">
              Official computer-assisted inspection platform. Statutory determinations remain subject to verification by authorized Legal Metrology Officers under Section 15 of the Legal Metrology Act, 2009.
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};
