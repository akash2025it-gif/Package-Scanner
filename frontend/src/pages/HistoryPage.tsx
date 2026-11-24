import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { Scan } from '../types';
import {
  Clock,
  Search,
  Filter,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  Download,
  PackageCheck,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialQ = searchParams.get('q') || '';

  const [scans, setScans] = useState<Scan[]>([]);
  const [searchQuery, setSearchQuery] = useState(initialQ);
  const [statusFilter, setStatusFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);

  const fetchScans = async () => {
    setIsLoading(true);
    try {
      const res = await api.getScans({ limit: 100 });
      setScans(res.items || []);
    } catch (err) {
      console.error('Failed to fetch inspection history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchScans();
  }, []);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q !== null) {
      setSearchQuery(q);
    }
  }, [searchParams]);

  const filteredScans = scans.filter((s) => {
    const matchesSearch =
      (s.product?.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.location_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.batch_number || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'compliant' && (s.status === 'reviewed' || s.status === 'closed')) ||
      (statusFilter === 'violation' && s.status === 'failed') ||
      (statusFilter === 'review' && (s.status === 'needs_review' || s.status === 'processing'));

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-blue-50 text-[#0051d5] border border-blue-200">
              Repository Archive
            </span>
          </div>
          <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
            Inspection History Repository
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Immutable archival record of all statutory packaged commodity inspections, laboratory findings, and compliance determinations.
          </p>
        </div>

        <button
          onClick={fetchScans}
          disabled={isLoading}
          className="p-2.5 rounded-2xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center gap-2 shadow-2xs transition-all cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[#0051d5]' : ''}`} />
          <span>Refresh Archive</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-3xl border border-slate-200/90 shadow-2xs flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by commodity name, batch code, or scan ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-300 text-xs focus:ring-2 focus:ring-[#0051d5]/20 focus:border-[#0051d5] focus:outline-none transition-all placeholder:text-slate-400"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-slate-400 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-300 p-2.5 text-xs bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:outline-none font-semibold text-slate-700"
          >
            <option value="all">All Determination Statuses</option>
            <option value="compliant">Compliant Consignments Only</option>
            <option value="violation">Statutory Violations Only</option>
            <option value="review">Pending Human Review Only</option>
          </select>
        </div>
      </div>

      {/* Scans Table */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase text-[10px] font-bold tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-3.5 px-5">Commodity / ID</th>
                <th className="py-3.5 px-4">Batch Code</th>
                <th className="py-3.5 px-4">Inspection Facility</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Inspection Date</th>
                <th className="py-3.5 px-5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-xs">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0051d5]" />
                    Loading repository inspection records...
                  </td>
                </tr>
              ) : filteredScans.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 text-xs">
                    <PackageCheck className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                    <p className="font-semibold text-slate-600">No inspection records match your filter criteria.</p>
                  </td>
                </tr>
              ) : (
                filteredScans.map((scan) => {
                  const isPass = scan.status === 'reviewed' || scan.status === 'closed';
                  const isFail = scan.status === 'failed';
                  const isReview = scan.status === 'needs_review' || scan.status === 'processing';

                  let badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                  let label = 'COMPLIANT';
                  if (isFail) {
                    badgeClass = 'bg-red-50 text-red-700 border-red-200';
                    label = 'NON-COMPLIANT';
                  } else if (isReview) {
                    badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
                    label = 'NEEDS REVIEW';
                  }

                  return (
                    <tr key={scan.id} className="hover:bg-blue-50/30 transition-colors group">
                      <td className="py-3.5 px-5">
                        <div className="font-bold text-slate-900 truncate max-w-[220px] group-hover:text-[#0051d5] transition-colors">
                          {scan.product?.name || scan.location_name || 'Packaged Commodity'}
                        </div>
                        <div className="text-[10px] font-mono text-slate-400">{scan.id.slice(0, 10)}...</div>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-600">
                        {scan.batch_number || '—'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 max-w-[180px] truncate">
                        {scan.location_name || 'Central Metrology Lab'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                          {isPass && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                          {isFail && <AlertCircle className="w-3 h-3 text-red-600" />}
                          {isReview && <HelpCircle className="w-3 h-3 text-amber-600" />}
                          <span>{label}</span>
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap text-[11px]">
                        {new Date(scan.created_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-3.5 px-5 text-right">
                        <Link
                          to={`/scan/${scan.id}`}
                          className="inline-flex items-center gap-1 font-bold text-xs text-[#0051d5] hover:text-[#003ea7] transition-colors"
                        >
                          <span>Inspect</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="p-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>Showing {filteredScans.length} of {scans.length} total inspections</span>
          <span className="font-semibold text-slate-600">LMPC Rules, 2011 Compliance Archival</span>
        </div>
      </div>
    </div>
  );
};
