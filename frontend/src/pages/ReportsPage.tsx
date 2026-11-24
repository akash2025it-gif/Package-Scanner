import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Scan } from '../types';
import {
  FileText,
  Download,
  FileCode,
  ShieldAlert,
  ChevronRight,
  ExternalLink,
  Printer,
  Search,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Sparkles,
  FileCheck2,
} from 'lucide-react';

export const ReportsPage: React.FC = () => {
  const [scans, setScans] = useState<Scan[]>([]);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGeneratingDoc, setIsGeneratingDoc] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    const fetchScans = async () => {
      try {
        const res = await api.getScans({ limit: 50 });
        setScans(res.items || []);
        if (res.items?.length > 0) {
          setSelectedScan(res.items[0]);
        }
      } catch (err) {
        console.error('Failed to load reports:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchScans();
  }, []);

  const downloadJsonReport = (scan: Scan) => {
    const reportData = {
      platform: "PackCheck AI – Legal Metrology Compliance Inspection Platform",
      report_version: "2.4",
      inspection_id: scan.id,
      timestamp: scan.created_at,
      status: scan.status,
      product: scan.product || { name: scan.location_name || "Unlabeled Sample" },
      batch_number: scan.batch_number,
      barcode_evidence: scan.metadata_json?.barcode_info || null,
      declarations: scan.declarations.map((d) => ({
        declaration: d.field_type,
        extracted_text: d.extracted_text,
        is_compliant: d.is_compliant,
        severity: d.severity,
        rule_reference: d.rule_reference,
        confidence_score: d.confidence_score,
        reviewer_override: d.reviewer_override,
        reviewer_notes: d.reviewer_notes,
      })),
      disclaimer: "STATUTORY NOTICE: This report is an AI-assisted technical inspection finding. It does not replace or supersede an official statutory certificate issued by a Legal Metrology Officer under the Legal Metrology Act, 2009."
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PackCheck_Inspection_${scan.id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handlePrint = () => {
    window.print();
  };

  const downloadOfficialReport = async (scan: Scan) => {
    setIsGeneratingDoc(true);
    try {
      const rep = await api.getScanReport(scan.id);
      await api.downloadReportPdf(rep.id, `compliance_report_${scan.id.slice(0, 8)}.pdf`);
    } catch (err: any) {
      alert('Failed to retrieve statutory report: ' + (err.message || 'Error'));
    } finally {
      setIsGeneratingDoc(false);
    }
  };

  const downloadDocxReport = async (scan: Scan) => {
    setIsGeneratingDoc(true);
    try {
      const rep = await api.getScanReport(scan.id);
      await api.downloadReportDocx(rep.id, `compliance_report_${scan.id.slice(0, 8)}.docx`);
    } catch (err: any) {
      alert('Failed to retrieve statutory DOCX dossier: ' + (err.message || 'Error'));
    } finally {
      setIsGeneratingDoc(false);
    }
  };

  const filteredScans = scans.filter((s) =>
    (s.product?.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.location_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (s.batch_number || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-blue-50 text-[#0051d5] border border-blue-200">
            Export & Verification
          </span>
        </div>
        <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
          Statutory Compliance Reports & Dossiers
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          Generate, preview, and download formal compliance inspection dossiers in authenticated PDF, Microsoft Word DOCX, and machine-readable JSON formats.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Side: Selectable Scans List (4 cols) */}
        <div className="lg:col-span-4 bg-white rounded-3xl border border-slate-200/90 shadow-2xs overflow-hidden h-[640px] flex flex-col no-print">
          <div className="p-4 border-b border-slate-200 space-y-2">
            <span className="font-bold text-xs text-slate-800 block">Select Inspection Dossier</span>
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search inspections..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-1 focus:ring-[#0051d5]"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {filteredScans.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">
                No inspections found matching search.
              </div>
            ) : (
              filteredScans.map((s) => {
                const isPass = s.status === 'reviewed' || s.status === 'closed';
                const isFail = s.status === 'failed';

                return (
                  <button
                    key={s.id}
                    onClick={() => setSelectedScan(s)}
                    className={`w-full p-3.5 text-left text-xs transition-colors block cursor-pointer ${
                      selectedScan?.id === s.id
                        ? 'bg-blue-50/80 border-l-4 border-[#0051d5]'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="font-bold text-slate-900 truncate">
                      {s.product?.name || s.location_name || 'Packaged Commodity'}
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                      <span className="font-mono text-slate-400">{s.id.slice(0, 10)}...</span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                          isPass
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : isFail
                            ? 'bg-red-50 text-red-700 border-red-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}
                      >
                        {isPass ? 'COMPLIANT' : isFail ? 'NON-COMPLIANT' : 'REVIEW'}
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Statutory Report Dossier Preview (8 cols) */}
        <div className="lg:col-span-8 bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-6 space-y-6">
          {selectedScan ? (
            <>
              {/* Report Actions Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200 no-print">
                <div className="flex items-center gap-2">
                  <FileCheck2 className="w-4 h-4 text-[#0051d5]" />
                  <span className="text-xs font-bold text-slate-800">Inspection Dossier Preview</span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => downloadOfficialReport(selectedScan)}
                    disabled={isGeneratingDoc}
                    className="px-3.5 py-1.5 rounded-xl bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{isGeneratingDoc ? 'Downloading...' : 'PDF Dossier'}</span>
                  </button>
                  <button
                    onClick={() => downloadDocxReport(selectedScan)}
                    disabled={isGeneratingDoc}
                    className="px-3.5 py-1.5 rounded-xl border border-emerald-700 hover:bg-emerald-50 text-emerald-800 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <FileCode className="w-3.5 h-3.5 text-emerald-700" />
                    <span>DOCX</span>
                  </button>
                  <button
                    onClick={handlePrint}
                    className="px-3.5 py-1.5 rounded-xl border border-slate-300 hover:bg-slate-50 text-xs font-bold text-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Printer className="w-3.5 h-3.5 text-[#0051d5]" />
                    <span>Print View</span>
                  </button>
                  <button
                    onClick={() => downloadJsonReport(selectedScan)}
                    className="px-3.5 py-1.5 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white text-xs font-bold flex items-center gap-1.5 shadow-xs transition-all cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>JSON</span>
                  </button>
                </div>
              </div>

              {/* Printable Statutory Document Preview */}
              <div className="border border-slate-300 p-8 rounded-2xl bg-white space-y-6 text-xs text-slate-800 shadow-xs font-sans print:border-none print:p-0">
                {/* Government Header */}
                <div className="text-center border-b pb-4 space-y-1">
                  <div className="text-[10px] uppercase font-bold tracking-widest text-slate-500">
                    Government of India • Ministry of Consumer Affairs, Food & Public Distribution
                  </div>
                  <h2 className="font-display font-black text-base text-slate-900 uppercase">
                    Department of Legal Metrology – Packaging Compliance Audit
                  </h2>
                  <div className="text-[11px] text-slate-500 font-medium">
                    Technical Inspection Dossier (Under Legal Metrology Packaged Commodities Rules, 2011)
                  </div>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Inspection Reference ID</span>
                    <span className="font-mono font-bold text-slate-900">{selectedScan.id}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Inspection Timestamp</span>
                    <span className="font-bold text-slate-900">{new Date(selectedScan.created_at).toLocaleString('en-IN')}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Product Description</span>
                    <span className="font-bold text-slate-900">{selectedScan.product?.name || 'Unlabeled Sample'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Batch / Lot Identification</span>
                    <span className="font-mono font-bold text-slate-900">{selectedScan.batch_number || 'N/A'}</span>
                  </div>
                </div>

                {/* Declarations Findings Summary */}
                <div className="space-y-3">
                  <h3 className="font-bold text-xs uppercase text-slate-900 border-b pb-1">
                    Rule 6 Statutory Declarations Verification Summary
                  </h3>
                  <table className="w-full text-left text-xs border border-slate-200">
                    <thead className="bg-slate-100 text-[10px] font-bold uppercase text-slate-600">
                      <tr>
                        <th className="p-2.5 border">Mandatory Field</th>
                        <th className="p-2.5 border">Declared Value On-Pack</th>
                        <th className="p-2.5 border">Rule Reference</th>
                        <th className="p-2.5 border">Result</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {selectedScan.declarations.map((d) => (
                        <tr key={d.id}>
                          <td className="p-2.5 border font-bold capitalize">{d.field_type.replace('_', ' ')}</td>
                          <td className="p-2.5 border font-mono text-[11px]">{d.extracted_text || '[Not detected]'}</td>
                          <td className="p-2.5 border text-[10px] text-slate-500">{d.rule_reference}</td>
                          <td className="p-2.5 border font-bold">
                            {d.is_compliant ? (
                              <span className="text-emerald-700">COMPLIANT</span>
                            ) : d.severity === 'needs_review' ? (
                              <span className="text-amber-700">NEEDS REVIEW</span>
                            ) : (
                              <span className="text-red-700">NON-COMPLIANT</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Statutory Disclaimer per Section 15 */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-300 text-[10px] text-slate-600 leading-relaxed space-y-1">
                  <div className="font-bold text-slate-900 uppercase">Statutory Limitations & Officer Verification Notice</div>
                  <p>
                    This technical report was generated through an AI-assisted computer vision and OCR inspection system. 
                    It serves as an investigative aid for authorized inspectors and <strong>does not constitute an official statutory legal certification or judicial penalty order</strong> under the Legal Metrology Act, 2009. 
                    Any enforcement seizure or legal notice must be accompanied by physical verification by an authorized Legal Metrology Officer.
                  </p>
                </div>
              </div>
            </>
          ) : (
            <div className="py-24 text-center text-slate-400 text-xs">
              Select an inspection record to preview its statutory dossier.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
