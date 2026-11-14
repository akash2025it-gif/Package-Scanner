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
      <div>
        <h1 className="font-display font-extrabold text-xl sm:text-2xl text-gray-900 tracking-tight">
          Settings & Profile
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Manage officer profile credentials, automation thresholds, and view legal engine operational status.
        </p>
      </div>

      {/* Officer Profile Card */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs space-y-4">
        <div className="flex items-center gap-3 border-b border-gray-100 pb-4">
          <div className="w-12 h-12 rounded-2xl bg-[#0051d5] text-white flex items-center justify-center font-extrabold text-base shadow-sm">
            {user?.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase() || 'PC'}
          </div>
          <div>
            <h2 className="font-display font-bold text-base text-gray-900">{user?.name}</h2>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-[#0051d5] border border-blue-200 uppercase">
                {user?.role}
              </span>
              <span className="text-xs text-gray-400">•</span>
              <span className="text-xs text-gray-500">{user?.email}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs pt-1">
          <div>
            <span className="text-gray-400 block text-[11px] font-semibold">Jurisdiction Region</span>
            <span className="font-bold text-gray-800">{user?.region || 'National HQ, New Delhi'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[11px] font-semibold">Assigned Division</span>
            <span className="font-bold text-gray-800">{user?.department || 'Central Legal Metrology Squad'}</span>
          </div>
          <div>
            <span className="text-gray-400 block text-[11px] font-semibold">Account Status</span>
            <span className="font-bold text-emerald-600 flex items-center gap-1 mt-0.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> Active Authorized Officer
            </span>
          </div>
        </div>
      </div>

      {/* Threshold Automation Settings (Administrator Only) */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs space-y-4">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <Sliders className="w-4 h-4 text-[#0051d5]" />
          <h2 className="font-display font-bold text-sm text-gray-900">
            Mandatory Declarations Automation & Verification Gate
          </h2>
        </div>

        {message && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{message}</span>
          </div>
        )}

        <form onSubmit={handleSaveThreshold} className="space-y-4 text-xs">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="font-semibold text-gray-700">
                Automatic Confirmation Confidence Threshold: <strong className="text-[#0051d5]">{threshold}%</strong>
              </label>
              <span className="text-gray-400 text-[11px]">Recommended: 80% - 90%</span>
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

          <p className="text-[11px] text-gray-500 leading-relaxed">
            Declarations with OCR confidence at or above <strong>{threshold}%</strong> without physical calibration conflict are automatically confirmed for inspection proceedings. Any declaration below this threshold is flagged for human officer review.
          </p>

          {isAdmin ? (
            <div className="pt-2 flex justify-end">
              <button
                type="submit"
                disabled={isSaving}
                className="px-5 py-2 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs shadow-sm transition-colors"
              >
                {isSaving ? 'Updating...' : 'Save Automation Threshold'}
              </button>
            </div>
          ) : (
            <div className="p-2.5 rounded-xl bg-gray-50 text-[11px] text-gray-500">
              Only Administrators have authority to modify system-wide automation thresholds.
            </div>
          )}
        </form>
      </div>

      {/* System Engine Health Card */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs space-y-4 text-xs">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-3">
          <Server className="w-4 h-4 text-emerald-600" />
          <h2 className="font-display font-bold text-sm text-gray-900">Engine Health & Runtime Topology</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 space-y-1">
            <span className="text-gray-400 text-[10px] uppercase font-bold block">Compliance Backend</span>
            <span className="font-bold text-gray-900 block">FastAPI 0.111+ (Python 3.14)</span>
            <span className="text-[10px] text-emerald-600 font-semibold">● Healthy / Operational</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 space-y-1">
            <span className="text-gray-400 text-[10px] uppercase font-bold block">Relational Database</span>
            <span className="font-bold text-gray-900 block">SQLAlchemy 2.0 Async</span>
            <span className="text-[10px] text-emerald-600 font-semibold">● packcheck.db Connected</span>
          </div>

          <div className="p-3.5 rounded-xl bg-gray-50 border border-gray-200 space-y-1">
            <span className="text-gray-400 text-[10px] uppercase font-bold block">Vision & OCR Engine</span>
            <span className="font-bold text-gray-900 block">OpenCV 5.0 + Native OCR</span>
            <span className="text-[10px] text-emerald-600 font-semibold">● QR & Barcode Active</span>
          </div>
        </div>
      </div>
    </div>
  );
};
