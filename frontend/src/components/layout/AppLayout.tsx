import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Navbar } from './Navbar';

export const AppLayout: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen bg-[#f8f9ff] overflow-hidden">
      <Sidebar isOpen={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Navbar onMenuToggle={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 flex flex-col justify-between">
          <div>
            <Outlet />
          </div>
          <footer className="mt-10 pt-4 pb-2 border-t border-gray-200 text-[11px] text-gray-500 flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>
              <span className="font-bold text-gray-700">PackCheck AI</span> • Legal Metrology (Packaged Commodities) Rules, 2011
            </div>
            <div className="text-[10px] text-gray-400 text-center sm:text-right">
              Statutory Notice: Computer-assisted inspection aid. Statutory determinations remain subject to verification by authorized Legal Metrology Officers under the Legal Metrology Act, 2009.
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
};
