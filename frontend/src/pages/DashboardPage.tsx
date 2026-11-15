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
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, canScan } = useAuth();
  const [scans, setScans] = useState<Scan[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [scansRes, analyticsRes] = await Promise.allSettled([
        api.getScans({ limit: 8 }),
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

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display font-extrabold text-xl sm:text-2xl text-gray-900 tracking-tight">
              Enforcement Overview
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-[#0051d5] border border-blue-200 uppercase">
              {user?.region || 'Central HQ'}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Welcome back, {user?.name}. Standard Legal Metrology compliance checks are active.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={loadData}
            className="p-2 rounded-xl border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 transition-colors"
            title="Refresh statistics"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          {canScan && (
            <Link
              to="/scan/new"
              className="px-4 py-2 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs flex items-center gap-2 shadow-sm transition-all"
            >
              <ScanLine className="w-4 h-4" />
              <span>Initiate New Scan</span>
            </Link>
          )}
        </div>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
            <span>Total Inspections</span>
            <span className="p-2 bg-blue-50 text-[#0051d5] rounded-xl"><ScanLine className="w-4 h-4" /></span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display font-extrabold text-2xl text-gray-900">{total}</span>
            <span className="text-[11px] text-gray-400 font-medium">commodities</span>
          </div>
          <div className="mt-3 text-[11px] text-gray-500 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
            <span>Across physical & digital retail</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
            <span>Compliant Packages</span>
            <span className="p-2 bg-emerald-50 text-emerald-600 rounded-xl"><ShieldCheck className="w-4 h-4" /></span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display font-extrabold text-2xl text-emerald-600">{compliantCount}</span>
            <span className="text-[11px] text-emerald-700/80 font-bold">({complianceRate}%)</span>
          </div>
          <div className="mt-3 text-[11px] text-emerald-600 flex items-center gap-1">
            <span>Meets all Rule 6 declarations</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
            <span>Statutory Violations</span>
            <span className="p-2 bg-red-50 text-red-600 rounded-xl"><AlertTriangle className="w-4 h-4" /></span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display font-extrabold text-2xl text-red-600">{nonCompliantCount}</span>
            <span className="text-[11px] text-gray-400 font-medium">cases</span>
          </div>
          <div className="mt-3 text-[11px] text-red-600 flex items-center gap-1">
            <span>Actionable non-compliances</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs">
          <div className="flex items-center justify-between text-gray-500 text-xs font-semibold">
            <span>Review Queue</span>
            <span className="p-2 bg-amber-50 text-amber-600 rounded-xl"><Clock className="w-4 h-4" /></span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="font-display font-extrabold text-2xl text-amber-600">{reviewCount}</span>
            <span className="text-[11px] text-gray-400 font-medium">pending</span>
          </div>
          <div className="mt-3 text-[11px] text-amber-700 flex items-center gap-1">
            <Link to="/review-queue" className="hover:underline flex items-center gap-1">
              <span>View pending reviews</span>
              <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content Split: Recent Inspections & Regulatory Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Inspections Table */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="font-display font-bold text-sm text-gray-900">Recent Commodity Inspections</h2>
              <p className="text-[11px] text-gray-500">Latest AI-analyzed packaged goods in your jurisdiction</p>
            </div>
            <Link
              to="/history"
              className="text-xs font-bold text-[#0051d5] hover:text-[#003ea7] flex items-center gap-1"
            >
              <span>View All</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 uppercase text-[10px] font-bold tracking-wider border-b border-gray-200">
                <tr>
                  <th className="py-3 px-4">Commodity / ID</th>
                  <th className="py-3 px-4">Batch No.</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
                {scans.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-gray-400 text-xs">
                      No inspections found in this database.
                    </td>
                  </tr>
                ) : (
                  scans.map((scan) => {
                    const isPass = scan.status === 'reviewed' || scan.status === 'closed';
                    const isFail = scan.status === 'failed';
                    const isReview = scan.status === 'needs_review' || scan.status === 'processing';

                    let badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                    let label = 'COMPLIANT';
                    if (isFail) {
                      badgeClass = 'bg-red-50 text-red-700 border-red-200';
                      label = 'VIOLATION';
                    } else if (isReview) {
                      badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
                      label = 'NEEDS REVIEW';
                    }

                    return (
                      <tr key={scan.id} className="hover:bg-blue-50/40 transition-colors">
                        <td className="py-3 px-4">
                          <div className="font-bold text-gray-900 truncate max-w-[200px]">
                            {scan.product?.name || scan.location_name || 'Packaged Commodity'}
                          </div>
                          <div className="text-[10px] font-mono text-gray-400">{scan.id.slice(0, 8)}...</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-gray-600">
                          {scan.batch_number || '—'}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${badgeClass}`}>
                            {label}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-500 whitespace-nowrap">
                          {new Date(scan.created_at).toLocaleDateString('en-IN', {
                            day: 'numeric',
                            month: 'short',
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Link
                            to={`/scan/${scan.id}`}
                            className="inline-flex items-center gap-1 font-bold text-xs text-[#0051d5] hover:text-[#003ea7]"
                          >
                            Inspect
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
        </div>

        {/* Regulatory Guidance Card */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-xs p-5 space-y-4">
          <div>
            <h2 className="font-display font-bold text-sm text-gray-900">Legal Metrology Rules, 2011</h2>
            <p className="text-[11px] text-gray-500">Key statutory declaration mandates</p>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <span className="font-bold text-gray-900 block text-[11px]">Rule 6(1)(f) – MRP & Taxes</span>
              <p className="text-gray-500 text-[11px] mt-0.5">
                Must state Maximum Retail Price with ₹ / Rs. symbol, followed by "Inclusive of all taxes".
              </p>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <span className="font-bold text-gray-900 block text-[11px]">Rule 6(1)(d) & Rule 8 – Net Quantity</span>
              <p className="text-gray-500 text-[11px] mt-0.5">
                Standard SI units required (g, kg, ml, l, N). Plural abbreviations like "gms" or "kgs" are prohibited.
              </p>
            </div>

            <div className="p-3 rounded-xl bg-gray-50 border border-gray-200">
              <span className="font-bold text-gray-900 block text-[11px]">Rule 6(1)(h) – Consumer Care</span>
              <p className="text-gray-500 text-[11px] mt-0.5">
                Complete redressal contact details: name, phone number, and official email address.
              </p>
            </div>
          </div>

          <Link
            to="/rules"
            className="w-full py-2.5 rounded-xl border border-gray-300 text-gray-700 font-bold text-xs flex items-center justify-center gap-2 hover:bg-gray-50 transition-colors"
          >
            <FileCheck2 className="w-4 h-4 text-[#0051d5]" />
            <span>Explore All Statutory Rules</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
