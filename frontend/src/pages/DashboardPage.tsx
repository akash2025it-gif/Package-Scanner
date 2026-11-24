import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Scan, AnalyticsSummary } from '../types';
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  ScanLine,
  ArrowUpRight,
  ChevronRight,
  TrendingUp,
  FileCheck2,
  RefreshCw,
  Search,
  Filter,
  PackageCheck,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, canScan } = useAuth();
  const [scans, setScans] = useState<Scan[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'compliant' | 'violation' | 'review'>('all');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [scansRes, analyticsRes] = await Promise.allSettled([
        api.getScans({ limit: 12 }),
        api.getAnalyticsSummary(),
      ]);

      if (scansRes.status === 'fulfilled') {
        setScans(scansRes.value.items || []);
      }
      if (analyticsRes.status === 'fulfilled') {
        setSummary(analyticsRes.value);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const total = summary?.total_inspections ?? scans.length;
  const compliantCount = summary?.compliant_count ?? scans.filter((s) => s.status === 'reviewed' || s.status === 'closed').length;
  const nonCompliantCount = summary?.non_compliant_count ?? scans.filter((s) => s.status === 'failed').length;
  const reviewCount = summary?.needs_review_count ?? scans.filter((s) => s.status === 'needs_review' || s.status === 'processing').length;
  const complianceRate = total > 0 ? Math.round((compliantCount / total) * 100) : 0;

  const filteredScans = scans.filter((s) => {
    const matchesSearch =
      (s.product?.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.location_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (s.batch_number || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      s.id.toLowerCase().includes(searchTerm.toLowerCase());

    const isPass = s.status === 'reviewed' || s.status === 'closed';
    const isFail = s.status === 'failed';
    const isRev = s.status === 'needs_review' || s.status === 'processing';

    if (statusFilter === 'compliant') return matchesSearch && isPass;
    if (statusFilter === 'violation') return matchesSearch && isFail;
    if (statusFilter === 'review') return matchesSearch && isRev;
    return matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Executive Header Banner */}
      <div className="relative overflow-hidden bg-gradient-to-r from-[#00174b] via-[#00287a] to-[#0051d5] rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-blue-950/10">
        <div className="absolute right-0 top-0 -mt-10 -mr-10 w-80 h-80 bg-blue-400/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-white/15 text-blue-200 border border-white/20">
                {user?.region || 'Central HQ'} • Squad 01
              </span>
              <span className="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                Live Deployment
              </span>
            </div>
            <h1 className="font-display font-black text-2xl sm:text-3xl tracking-tight text-white">
              Legal Metrology Inspection Command
            </h1>
            <p className="text-xs sm:text-sm text-blue-100/85 max-w-2xl leading-relaxed">
              Automated statutory compliance inspection under Legal Metrology (Packaged Commodities) Rules, 2011. Pre-OCR blur filtering, Rule 6 statutory checks, and verifiable audit dossiers.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={loadData}
              disabled={isLoading}
              className="p-3 rounded-2xl bg-white/10 hover:bg-white/20 text-white border border-white/15 transition-all shadow-sm"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            {canScan && (
              <Link
                to="/scan/new"
                className="px-5 py-3 rounded-2xl bg-white text-[#00174b] hover:bg-blue-50 font-extrabold text-xs flex items-center gap-2 shadow-lg hover:shadow-xl hover:scale-102 transition-all"
              >
                <ScanLine className="w-4 h-4 text-[#0051d5]" />
                <span>Initiate New Scan</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* KPI & Compliance Health Score Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Inspections Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Total Inspections</span>
            <span className="p-2.5 bg-blue-50 text-[#0051d5] rounded-xl"><ScanLine className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-display font-black text-3xl text-slate-900">{total}</span>
            <span className="text-[11px] text-slate-400 font-medium">units audited</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 flex items-center gap-1 font-medium">
            <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
            <span>Retail & warehouse consignments</span>
          </div>
        </div>

        {/* Compliance Health Score Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Compliance Rate</span>
            <span className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl"><ShieldCheck className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-display font-black text-3xl text-emerald-600">{complianceRate}%</span>
            <span className="text-[11px] text-emerald-700/90 font-bold">({compliantCount} compliant)</span>
          </div>
          <div className="mt-3">
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, complianceRate))}%` }}
              />
            </div>
          </div>
        </div>

        {/* Violations Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Statutory Violations</span>
            <span className="p-2.5 bg-red-50 text-red-600 rounded-xl"><AlertTriangle className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-display font-black text-3xl text-red-600">{nonCompliantCount}</span>
            <span className="text-[11px] text-red-700/80 font-bold">breaches</span>
          </div>
          <div className="mt-3 text-[11px] text-red-600 flex items-center gap-1 font-medium">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Rule 6 non-compliance flagged</span>
          </div>
        </div>

        {/* Review Queue Card */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between text-slate-500 text-xs font-semibold">
            <span>Review Queue</span>
            <span className="p-2.5 bg-amber-50 text-amber-600 rounded-xl"><Clock className="w-4 h-4" /></span>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="font-display font-black text-3xl text-amber-600">{reviewCount}</span>
            <span className="text-[11px] text-amber-700 font-medium">awaiting review</span>
          </div>
          <div className="mt-3 text-[11px] text-amber-700 flex items-center gap-1 font-semibold">
            <Link to="/review-queue" className="hover:underline flex items-center gap-1">
              <span>Inspect pending items</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Split View: Recent Inspections Feed & Statutory Guidance */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Recent Inspections Table with Filters */}
        <div className="lg:col-span-8 bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden">
          {/* Table Header & Controls */}
          <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="font-display font-bold text-sm text-slate-900">Recent Package Inspections</h2>
              <p className="text-[11px] text-slate-500">Live feed of scanned commodities and automated statutory determinations</p>
            </div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Filter table..."
                  className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#0051d5] w-36 sm:w-44"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="py-1.5 px-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none text-slate-700 font-semibold"
              >
                <option value="all">All</option>
                <option value="compliant">Compliant</option>
                <option value="violation">Violations</option>
                <option value="review">Needs Review</option>
              </select>
            </div>
          </div>

          {/* Table Content */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50/80 text-slate-500 uppercase text-[10px] font-bold tracking-wider border-b border-slate-200">
                <tr>
                  <th className="py-3.5 px-5">Commodity / ID</th>
                  <th className="py-3.5 px-4">Batch / Lot</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400 text-xs">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0051d5]" />
                      Synchronizing commodity inspections...
                    </td>
                  </tr>
                ) : filteredScans.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400 text-xs">
                      <PackageCheck className="w-8 h-8 mx-auto mb-2 text-slate-300" />
                      <p className="font-semibold text-slate-600">No inspections match the current criteria.</p>
                      {canScan && (
                        <Link
                          to="/scan/new"
                          className="mt-2 inline-flex items-center gap-1.5 text-[#0051d5] font-bold hover:underline"
                        >
                          <ScanLine className="w-3.5 h-3.5" />
                          <span>Initiate a scan</span>
                        </Link>
                      )}
                    </td>
                  </tr>
                ) : (
                  filteredScans.map((scan) => {
                    const isPass = scan.status === 'reviewed' || scan.status === 'closed';
                    const isFail = scan.status === 'failed';
                    const isReview = scan.status === 'needs_review' || scan.status === 'processing';

                    let badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200/80';
                    let label = 'COMPLIANT';
                    if (isFail) {
                      badgeClass = 'bg-red-50 text-red-700 border-red-200/80';
                      label = 'NON-COMPLIANT';
                    } else if (isReview) {
                      badgeClass = 'bg-amber-50 text-amber-700 border-amber-200/80';
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
                        <td className="py-3.5 px-4">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ${badgeClass}`}>
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

          <div className="p-3.5 bg-slate-50/80 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <span>Showing {filteredScans.length} of {scans.length} recent records</span>
            <Link to="/history" className="font-bold text-[#0051d5] hover:underline flex items-center gap-1">
              <span>View full history archive</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Right Column (4 cols): Statutory Reference & Quick Guidance */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-[#0051d5]" />
                <h2 className="font-display font-bold text-sm text-slate-900">Statutory Declarations</h2>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-[#0051d5] border border-blue-200">
                Rule 6(1)
              </span>
            </div>

            <div className="space-y-2.5 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-0.5">
                <span className="font-bold text-slate-900 text-[11px] block">Rule 6(1)(f) – Maximum Retail Price</span>
                <p className="text-slate-600 text-[11px] leading-relaxed">
                  MRP in ₹ with exact phrasing: <em>"Inclusive of all taxes"</em> or <em>"Incl. of all taxes"</em>.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-0.5">
                <span className="font-bold text-slate-900 text-[11px] block">Rule 6(1)(d) & Rule 8 – Net Quantity</span>
                <p className="text-slate-600 text-[11px] leading-relaxed">
                  Only SI units (g, kg, ml, l, N). Illegal abbreviations: <em>"gms", "kgs", "ltrs"</em>.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-0.5">
                <span className="font-bold text-slate-900 text-[11px] block">Rule 6(1)(h) – Consumer Care</span>
                <p className="text-slate-600 text-[11px] leading-relaxed">
                  Full redressal contact: Officer name, working phone number, and official email address.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 space-y-0.5">
                <span className="font-bold text-slate-900 text-[11px] block">First Schedule – Minimum Font Slabs</span>
                <p className="text-slate-600 text-[11px] leading-relaxed">
                  Height slabs for PDP numerals from 1.0mm up to 6.0mm based on packaging net quantity.
                </p>
              </div>
            </div>

            <Link
              to="/rules"
              className="w-full py-2.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs flex items-center justify-center gap-2 transition-colors"
            >
              <span>Explore Statutory Rule Engine</span>
              <ArrowUpRight className="w-3.5 h-3.5 text-[#0051d5]" />
            </Link>
          </div>

          {/* Quick Shortcuts */}
          <div className="bg-gradient-to-br from-blue-50/80 to-indigo-50/80 rounded-3xl border border-blue-200/70 p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-[#00174b]">
              <Sparkles className="w-4 h-4 text-[#0051d5]" />
              <span>Inspector Quick Links</span>
            </div>
            <div className="grid grid-cols-2 gap-2 pt-1 text-xs">
              <Link
                to="/reports"
                className="p-2.5 rounded-xl bg-white/90 border border-blue-200 text-[#00174b] font-bold hover:bg-white transition-all text-center"
              >
                Dossier Reports
              </Link>
              <Link
                to="/review-queue"
                className="p-2.5 rounded-xl bg-white/90 border border-blue-200 text-[#00174b] font-bold hover:bg-white transition-all text-center"
              >
                Review Queue
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
