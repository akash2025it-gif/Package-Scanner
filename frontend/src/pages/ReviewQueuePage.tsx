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
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-display font-extrabold text-xl sm:text-2xl text-gray-900 tracking-tight">
            Human Review Queue
          </h1>
          <p className="text-xs text-gray-500 mt-1">
            Packages with uncertain findings, physical calibration requirements, or extraction conflicts pending inspector verification.
          </p>
        </div>
        <button
          onClick={loadQueue}
          className="p-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors flex items-center gap-1.5 text-xs font-semibold"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-amber-50/60 border-b border-amber-200 text-xs text-amber-900 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            {scans.length} inspection(s) currently require manual verification before final statutory determination.
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase text-[10px] font-bold tracking-wider border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Commodity / Scan ID</th>
                <th className="py-3 px-4">Batch Number</th>
                <th className="py-3 px-4">Flagged Findings</th>
                <th className="py-3 px-4">Time in Queue</th>
                <th className="py-3 px-4 text-right">Review Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-400">
                    Loading queue records...
                  </td>
                </tr>
              ) : scans.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-gray-400">
                    <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
                    <p className="font-bold text-gray-700">Review queue is clear!</p>
                    <p className="text-[11px] text-gray-400 mt-0.5">
                      All high-confidence declarations have been resolved.
                    </p>
                  </td>
                </tr>
              ) : (
                scans.map((scan) => {
                  const pendingCount = scan.declarations?.filter(
                    (d) => d.severity === 'needs_review' || (!d.is_compliant && d.confidence_score < 0.7)
                  ).length || 1;

                  return (
                    <tr key={scan.id} className="hover:bg-amber-50/20 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-gray-900 truncate max-w-[240px]">
                          {scan.product?.name || scan.location_name || 'Packaged Commodity'}
                        </div>
                        <div className="text-[10px] font-mono text-gray-400">{scan.id}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-600">
                        {scan.batch_number || '—'}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                          {pendingCount} item(s) need review
                        </span>
                      </td>
                      <td className="py-3 px-4 text-gray-500 text-[11px]">
                        {new Date(scan.created_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={`/scan/${scan.id}`}
                          className="px-3 py-1.5 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs inline-flex items-center gap-1 transition-colors"
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
