import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
} from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
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
    fetchScans();
  }, []);

  const filteredScans = scans.filter((s) => {
    const matchesSearch =
      (s.product?.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
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
      <div>
        <h1 className="font-display font-extrabold text-xl sm:text-2xl text-gray-900 tracking-tight">
          Inspection History Repository
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Historical record of all statutory packaged commodity inspections and findings.
        </p>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by commodity, batch, or ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-xl border border-gray-300 text-xs focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-gray-400 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border border-gray-300 p-2 text-xs bg-white focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="compliant">Compliant Only</option>
            <option value="violation">Violations Only</option>
            <option value="review">Needs Review Only</option>
          </select>
        </div>
      </div>

      {/* Scans Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase text-[10px] font-bold tracking-wider border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Commodity / ID</th>
                <th className="py-3 px-4">Batch Code</th>
                <th className="py-3 px-4">Location</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Inspection Date</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400">
                    Loading records...
                  </td>
                </tr>
              ) : filteredScans.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400">
                    No matching inspection records found.
                  </td>
                </tr>
              ) : (
                filteredScans.map((scan) => {
                  const isPass = scan.status === 'reviewed' || scan.status === 'closed';
                  const isFail = scan.status === 'failed';
                  const isReview = scan.status === 'needs_review' || scan.status === 'processing';

                  let badge = (
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      COMPLIANT
                    </span>
                  );
                  if (isFail) {
                    badge = (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                        VIOLATION
                      </span>
                    );
                  } else if (isReview) {
                    badge = (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        NEEDS REVIEW
                      </span>
                    );
                  }

                  return (
                    <tr key={scan.id} className="hover:bg-blue-50/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-bold text-gray-900 truncate max-w-[220px]">
                          {scan.product?.name || scan.location_name || 'Packaged Commodity'}
                        </div>
                        <div className="text-[10px] font-mono text-gray-400">{scan.id}</div>
                      </td>
                      <td className="py-3 px-4 font-mono text-gray-600">
                        {scan.batch_number || '—'}
                      </td>
                      <td className="py-3 px-4 text-gray-500 truncate max-w-[160px]">
                        {scan.location_name || 'Inspection Lab'}
                      </td>
                      <td className="py-3 px-4">{badge}</td>
                      <td className="py-3 px-4 text-gray-500 whitespace-nowrap">
                        {new Date(scan.created_at).toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          to={`/scan/${scan.id}`}
                          className="inline-flex items-center gap-1 font-bold text-xs text-[#0051d5] hover:text-[#003ea7]"
                        >
                          View Details
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
    </div>
  );
};
