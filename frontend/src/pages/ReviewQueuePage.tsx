import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { Scan } from '../types';
import {
  ClipboardCheck,
  AlertTriangle,
  Clock,
  ChevronRight,
  Eye,
  CheckCircle2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

export const ReviewQueuePage: React.FC = () => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadQueue = async () => {
    setIsLoading(true);
    try {
      const res = await api.getScans({ status: 'needs_review', limit: 100 });
      setScans(res.items || []);
    } catch (err) {
      console.error('Failed to load review queue:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-amber-50 text-amber-800 border border-amber-200">
              Inspector Verification
            </span>
          </div>
          <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
            Human Verification Queue
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Packages with border OCR ambiguity, borderline font heights, or extraction conflicts pending inspector manual determination before statutory closure.
          </p>
        </div>
        <button
          onClick={loadQueue}
          disabled={isLoading}
          className="p-2.5 rounded-2xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors flex items-center gap-2 text-xs font-bold shadow-2xs cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[#0051d5]' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="p-4 bg-gradient-to-r from-amber-50/80 to-amber-100/40 border-b border-amber-200 text-xs text-amber-900 flex items-center justify-between">
          <div className="flex items-center gap-2 font-medium">
            <Clock className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>{scans.length} inspection(s)</strong> require manual confirmation before final statutory determination.
            </span>
          </div>
          <span className="text-[10px] font-bold text-amber-800/80 uppercase tracking-wider">
            High Priority
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-bold tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-5">Commodity / Scan ID</th>
                <th className="py-3.5 px-4">Batch Number</th>
                <th className="py-3.5 px-4">Flagged Findings</th>
                <th className="py-3.5 px-4">Time in Queue</th>
                <th className="py-3.5 px-5 text-right">Review Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0051d5]" />
                    Loading pending queue items...
                  </td>
                </tr>
              ) : scans.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-16 text-center text-slate-400">
                    <div className="w-12 h-12 rounded-3xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3 shadow-xs">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                    <p className="font-bold text-sm text-slate-800">Review queue is clear!</p>
                    <p className="text-[11px] text-slate-500 mt-1 max-w-sm mx-auto">
                      All high-confidence declarations have been resolved. New flagged packages will appear here automatically.
                    </p>
                  </td>
                </tr>
              ) : (
                scans.map((scan) => {
                  const pendingCount = scan.declarations?.filter(
                    (d) => d.severity === 'needs_review' || (!d.is_compliant && d.confidence_score < 0.7)
                  ).length || 1;

                  return (
                    <tr key={scan.id} className="hover:bg-amber-50/25 transition-colors group">
                      <td className="py-3.5 px-5">
                        <div className="font-bold text-slate-900 truncate max-w-[240px] group-hover:text-[#0051d5] transition-colors">
                          {scan.product?.name || scan.location_name || 'Packaged Commodity'}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">{scan.id.slice(0, 10)}...</div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        {scan.batch_number || '—'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                          {pendingCount} field(s) require review
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                        {new Date(scan.created_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <Link
                          to={`/scan/${scan.id}`}
                          className="px-3.5 py-1.5 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs inline-flex items-center gap-1.5 transition-all shadow-xs cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>Review Finding</span>
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
