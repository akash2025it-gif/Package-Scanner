import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { AnalyticsSummary } from '../types';
import {
  BarChart3,
  TrendingUp,
  PieChart,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  MapPin,
  PackageCheck,
  Info,
  Sparkles,
  Layers,
} from 'lucide-react';

export const AnalyticsPage: React.FC = () => {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchAnalytics = async () => {
    setIsLoading(true);
    try {
      const data = await api.getAnalyticsSummary();
      setSummary(data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const total = summary?.total_inspections ?? 0;
  const compliant = summary?.compliant_count ?? 0;
  const violations = summary?.non_compliant_count ?? 0;
  const review = summary?.needs_review_count ?? 0;
  const complianceRate = total > 0 ? Math.round((compliant / total) * 100) : 0;

  // Use real backend most common findings
  const topViolations = summary?.most_common_findings && summary.most_common_findings.length > 0
    ? summary.most_common_findings.map((f) => ({
        name: f.finding_name,
        count: f.total_violations || f.affected_inspections,
        rule: f.rule_reference,
      }))
    : (summary?.top_violations || []);

  const regionalBreakdown = summary?.regional_overview && summary.regional_overview.length > 0
    ? summary.regional_overview.map((r) => ({
        region: r.region,
        total: r.total_inspections,
        rate: `${Math.round(100 - (r.violation_rate || 0))}%`,
        status: (r.violation_rate || 0) > 20 ? 'Attention Required' : 'Normal',
      }))
    : [];

  const categoryRisks = summary?.product_risk_overview || [];
  const dynamicInsights = summary?.dynamic_insights || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-blue-50 text-[#0051d5] border border-blue-200">
              Regulatory Intelligence
            </span>
          </div>
          <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
            Enforcement & Compliance Analytics
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
            Real-time regulatory metrics, violation frequency distributions, and regional inspection throughput under LMPC Rules, 2011.
          </p>
        </div>
        <button
          onClick={fetchAnalytics}
          disabled={isLoading}
          className="p-2.5 rounded-2xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 transition-colors flex items-center gap-2 text-xs font-bold shadow-2xs cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-[#0051d5]' : ''}`} />
          <span>Refresh Data</span>
        </button>
      </div>

      {/* Dynamic Statutory Insights */}
      {dynamicInsights.length > 0 && (
        <div className="p-5 rounded-3xl bg-gradient-to-r from-blue-50 via-indigo-50/70 to-blue-50 border border-blue-200/80 text-[#00174b] text-xs space-y-2 shadow-2xs">
          <div className="flex items-center gap-2 font-bold text-[#0051d5]">
            <Sparkles className="w-4 h-4 shrink-0" />
            <span className="font-display text-sm">Active Enforcement Intelligence</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-slate-700 pl-1 leading-relaxed">
            {dynamicInsights.map((insight, idx) => (
              <li key={idx}>{insight}</li>
            ))}
          </ul>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
        <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <span className="text-slate-400 font-semibold block text-[11px]">Total Inspections Audited</span>
          <span className="font-display font-black text-3xl text-slate-900 block mt-1.5">{total}</span>
          <span className="text-[11px] text-slate-500 mt-2 block font-medium">100% verified against LMPC 2011</span>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <span className="text-slate-400 font-semibold block text-[11px]">Overall Compliance Rate</span>
          <span className="font-display font-black text-3xl text-emerald-600 block mt-1.5">{complianceRate}%</span>
          <span className="text-[11px] text-emerald-700 font-bold mt-2 block">{compliant} compliant commodities</span>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <span className="text-slate-400 font-semibold block text-[11px]">Statutory Violations</span>
          <span className="font-display font-black text-3xl text-red-600 block mt-1.5">{violations}</span>
          <span className="text-[11px] text-red-600 font-bold mt-2 block">Actionable legal breaches</span>
        </div>

        <div className="bg-white p-5 rounded-3xl border border-slate-200/90 shadow-2xs hover:shadow-md transition-shadow">
          <span className="text-slate-400 font-semibold block text-[11px]">Under Officer Review</span>
          <span className="font-display font-black text-3xl text-amber-600 block mt-1.5">{review}</span>
          <span className="text-[11px] text-amber-700 font-bold mt-2 block">Pending verification queue</span>
        </div>
      </div>

      {/* Analytics Breakdown Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Most Frequent Violations (7 cols) */}
        <div className="lg:col-span-7 bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="font-display font-bold text-sm text-slate-900">
                Frequently Detected Statutory Violations
              </h2>
              <p className="text-[11px] text-slate-500">Distribution of non-compliant label declarations</p>
            </div>
            <BarChart3 className="w-4 h-4 text-[#0051d5]" />
          </div>

          {topViolations.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              No statutory violations detected across currently finalized inspection records.
            </div>
          ) : (
            <div className="space-y-4 text-xs">
              {topViolations.map((v, i) => {
                const maxCount = Math.max(...topViolations.map((o) => o.count), 1);
                const percentage = Math.round((v.count / maxCount) * 100);

                return (
                  <div key={i} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800">{v.name}</span>
                      <span className="font-mono text-slate-500 font-bold">{v.count} violations</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-[#0051d5] h-full rounded-full transition-all duration-500"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Regional Jurisdiction Breakdown (5 cols) */}
        <div className="lg:col-span-5 bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="font-display font-bold text-sm text-slate-900">Regional Jurisdiction Breakdown</h2>
              <p className="text-[11px] text-slate-500">Inspection throughput by zonal field squad</p>
            </div>
            <MapPin className="w-4 h-4 text-purple-600" />
          </div>

          {regionalBreakdown.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-400">
              All scans recorded under Central Headquarters Jurisdiction.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 text-xs">
              {regionalBreakdown.map((r, i) => (
                <div key={i} className="py-3 flex items-center justify-between">
                  <div>
                    <span className="font-bold text-slate-900 block">{r.region}</span>
                    <span className="text-[11px] text-slate-400">{r.total} packages inspected</span>
                  </div>
                  <div className="text-right">
                    <span className="font-bold text-emerald-700 block">{r.rate} Compliant</span>
                    <span className="text-[10px] text-slate-500">{r.status}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="p-3 rounded-2xl bg-slate-50 text-[10px] text-slate-500 leading-tight border border-slate-200/70">
            * Regional metrics reflect actual verified database records across all authorized inspection devices.
          </div>
        </div>
      </div>

      {/* Commodity Category Risk Heatmap */}
      {categoryRisks.length > 0 && (
        <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h2 className="font-display font-bold text-sm text-slate-900">Commodity Category Risk Analysis</h2>
              <p className="text-[11px] text-slate-500">Observed compliance rate categorized by commodity type</p>
            </div>
            <PackageCheck className="w-4 h-4 text-emerald-600" />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {categoryRisks.map((cat, idx) => (
              <div key={idx} className="p-4 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900">{cat.category}</span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      cat.risk_level === 'HIGH'
                        ? 'bg-red-100 text-red-700'
                        : cat.risk_level === 'MEDIUM'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-emerald-100 text-emerald-700'
                    }`}
                  >
                    {cat.risk_level} RISK
                  </span>
                </div>
                <div className="flex justify-between text-slate-500 text-[11px]">
                  <span>Total Inspected:</span>
                  <span className="font-bold text-slate-800">{cat.total_inspections}</span>
                </div>
                <div className="flex justify-between text-slate-500 text-[11px]">
                  <span>Violations Found:</span>
                  <span className="font-bold text-red-600">{cat.non_compliant_count}</span>
                </div>
                <div className="flex justify-between text-slate-500 text-[11px]">
                  <span>Compliance Rate:</span>
                  <span className="font-bold text-emerald-700">
                    {cat.compliance_rate !== undefined && cat.compliance_rate !== null ? `${cat.compliance_rate}%` : 'N/A'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
