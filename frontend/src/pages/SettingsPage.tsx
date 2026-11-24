import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Settings,
  Shield,
  Sliders,
  CheckCircle2,
  Server,
  Database,
  Cpu,
  User as UserIcon,
  Sparkles,
  Layers,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { user, isAdmin } = useAuth();
  const [threshold, setThreshold] = useState<number>(80);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const config = await api.getAutomationConfig();
        if (config?.auto_confirm_threshold !== undefined) {
          setThreshold(config.auto_confirm_threshold);
        }
      } catch (err) {
        console.warn('Could not fetch automation config:', err);
      }
    };
    fetchConfig();
  }, []);

  const handleSaveThreshold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAdmin) return;
    setIsSaving(true);
    setMessage(null);
    try {
      await api.updateAutomationConfig(threshold);
      setMessage('Automatic confirmation threshold updated successfully.');
      setTimeout(() => setMessage(null), 3000);
    } catch (err: any) {
      alert('Failed to update threshold: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-blue-50 text-[#0051d5] border border-blue-200">
            System Administration
          </span>
        </div>
        <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
          Settings & Officer Configuration
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          Manage officer credentials, configure automatic verification thresholds, and monitor real-time engine telemetry.
        </p>
      </div>

      {/* Officer Profile Card */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-2xs space-y-4">
        <div className="flex items-center gap-3.5 border-b border-slate-100 pb-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#00174b] to-[#0051d5] text-white flex items-center justify-center font-black text-lg shadow-md shadow-blue-900/20">
            {user?.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase() || 'PC'}
          </div>
          <div>
            <h2 className="font-display font-black text-lg text-slate-900">{user?.name}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-50 text-[#0051d5] border border-blue-200 uppercase tracking-wide">
                {user?.role}
              </span>
              <span className="text-xs text-slate-300">•</span>
              <span className="text-xs text-slate-500 font-medium">{user?.email}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs pt-1">
          <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200/70">
            <span className="text-slate-400 block text-[10px] font-bold uppercase">Jurisdiction Region</span>
            <span className="font-bold text-slate-800 text-xs mt-0.5 block">{user?.region || 'National HQ, New Delhi'}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200/70">
            <span className="text-slate-400 block text-[10px] font-bold uppercase">Assigned Division</span>
            <span className="font-bold text-slate-800 text-xs mt-0.5 block">{user?.department || 'Central Legal Metrology Squad'}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-2xl border border-slate-200/70">
            <span className="text-slate-400 block text-[10px] font-bold uppercase">Account Status</span>
            <span className="font-bold text-emerald-600 flex items-center gap-1.5 mt-0.5 text-xs">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active Authorized Officer
            </span>
          </div>
        </div>
      </div>

      {/* Threshold Automation Settings (Administrator Only) */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-2xs space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Sliders className="w-4 h-4 text-[#0051d5]" />
          <h2 className="font-display font-bold text-sm text-slate-900">
            Mandatory Declarations Automation & Verification Gate
          </h2>
        </div>

        {message && (
          <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl text-xs flex items-center gap-2.5 shadow-2xs">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="font-semibold">{message}</span>
          </div>
        )}

        <form onSubmit={handleSaveThreshold} className="space-y-4 text-xs">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="font-semibold text-slate-700">
                Automatic Confirmation Confidence Threshold: <strong className="text-[#0051d5] text-sm">{threshold}%</strong>
              </label>
              <span className="text-slate-400 text-[11px]">Recommended: 80% - 90%</span>
            </div>
            <input
              type="range"
              min="50"
              max="99"
              step="1"
              disabled={!isAdmin}
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-[#0051d5] cursor-pointer"
            />
          </div>

          <p className="text-[11px] text-slate-500 leading-relaxed">
            Declarations with OCR confidence at or above <strong>{threshold}%</strong> without physical calibration conflict are automatically confirmed for inspection proceedings. Any declaration below this threshold is flagged for human officer review.
          </p>

          {isAdmin ? (
            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={isSaving}
                className="px-5 py-2.5 rounded-2xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs shadow-md transition-all cursor-pointer"
              >
                {isSaving ? 'Updating...' : 'Save Automation Threshold'}
              </button>
            </div>
          ) : (
            <div className="p-3 rounded-2xl bg-slate-50 text-[11px] text-slate-500 border border-slate-200/70">
              Only Administrators have authority to modify system-wide automation thresholds.
            </div>
          )}
        </form>
      </div>

      {/* System Engine Health Card */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-2xs space-y-4 text-xs">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Server className="w-4 h-4 text-emerald-600" />
          <h2 className="font-display font-bold text-sm text-slate-900">Engine Health & Runtime Topology</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="text-slate-400 text-[10px] uppercase font-bold block">Compliance Backend</span>
            <span className="font-bold text-slate-900 block text-xs">FastAPI 0.111+ (Python 3.14)</span>
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-700 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Healthy / Operational</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="text-slate-400 text-[10px] uppercase font-bold block">Relational Database</span>
            <span className="font-bold text-slate-900 block text-xs">SQLAlchemy 2.0 Async</span>
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-700 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>PostgreSQL / SQLite Driver Active</span>
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
            <span className="text-slate-400 text-[10px] uppercase font-bold block">Vision & OCR Pipeline</span>
            <span className="font-bold text-slate-900 block text-xs">OpenCV 5.0 + Native OCR</span>
            <div className="flex items-center gap-1.5 text-[10px] text-emerald-700 font-bold">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span>2D QR & 1D Barcode Decoders Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
