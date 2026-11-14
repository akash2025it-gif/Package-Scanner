import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Scan, DeclarationFinding, AuditLog } from '../types';
import { ImageCanvas } from '../components/scan/ImageCanvas';
import { DeclarationEditorModal } from '../components/scan/DeclarationEditorModal';
import {
  ShieldCheck,
  AlertTriangle,
  Clock,
  QrCode,
  FileText,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Edit3,
  History,
  Download,
  Check,
  X,
  ExternalLink,
} from 'lucide-react';

export const ScanDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { canScan } = useAuth();
  const [scan, setScan] = useState<Scan | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [editingFinding, setEditingFinding] = useState<DeclarationFinding | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadScanData = async () => {
    if (!id) return;
    try {
      const data = await api.getScan(id);
      setScan(data);
      const logs = await api.getAuditTrail(id);
      setAuditLogs(logs || []);
    } catch (err: any) {
      console.error('Failed to load scan:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadScanData();
  }, [id]);

  if (isLoading) {
    return (
      <div className="py-20 text-center text-xs text-gray-500">
        Loading commodity inspection records...
      </div>
    );
  }

  if (!scan) {
    return (
      <div className="py-16 text-center text-xs text-red-600 bg-red-50 rounded-2xl p-6 border border-red-200">
        Scan record not found or inaccessible.
      </div>
    );
  }

  const primaryImage = scan.images?.[0]?.image_url || '/logo.png';
  const barcodeInfo = scan.metadata_json?.barcode_info;
  const declarations = scan.declarations || [];

  const handleQuickReview = async (declId: string, action: 'confirm' | 'reject') => {
    if (!id) return;
    try {
      await api.reviewDeclaration(id, declId, {
        action,
        reviewer_notes: action === 'confirm' ? 'Confirmed by inspector' : 'Rejected by inspector',
      });
      setActionMessage(`Declaration finding marked as ${action.toUpperCase()}`);
      setTimeout(() => setActionMessage(null), 3000);
      await loadScanData();
    } catch (err: any) {
      alert('Review action failed: ' + err.message);
    }
  };

  const handleSaveCorrection = async (payload: { extracted_text?: string; is_compliant?: boolean; notes?: string }) => {
    if (!id || !editingFinding) return;
    await api.updateDeclaration(id, editingFinding.id, payload);
    setActionMessage('Declaration correction saved and re-validated');
    setTimeout(() => setActionMessage(null), 3000);
    await loadScanData();
  };

  const handleFinalize = async () => {
    if (!id) return;
    const confirm = window.confirm('Finalize inspection and record statutory determination?');
    if (!confirm) return;
    try {
      await api.finalizeScan(id);
      await loadScanData();
      alert('Inspection finalized successfully.');
    } catch (err: any) {
      alert('Finalization failed: ' + err.message);
    }
  };

  const isFinalized = scan.status === 'reviewed' || scan.status === 'closed';

  return (
    <div className="space-y-6">
      {/* Top Inspection Summary Header */}
      <div className="bg-white p-5 rounded-2xl border border-gray-200 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-display font-extrabold text-xl text-gray-900 tracking-tight">
              {scan.product?.name || scan.location_name || 'Packaged Commodity Inspection'}
            </h1>
            <span
              className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border uppercase ${
                scan.status === 'reviewed' || scan.status === 'closed'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : scan.status === 'failed'
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              {scan.status.replace('_', ' ')}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mt-1">
            <span className="font-mono text-gray-400">ID: {scan.id}</span>
            <span>•</span>
            <span>Batch: {scan.batch_number || 'N/A'}</span>
            <span>•</span>
            <span>Inspected on: {new Date(scan.created_at).toLocaleString('en-IN')}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/reports`}
            className="px-3.5 py-2 rounded-xl border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold text-xs flex items-center gap-1.5 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-[#0051d5]" />
            <span>Generate Report</span>
          </Link>
          {canScan && !isFinalized && (
            <button
              onClick={handleFinalize}
              className="px-4 py-2 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-bold text-xs shadow-sm transition-all"
            >
              Finalize Inspection
            </button>
          )}
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Two-Column Inspection Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Interactive Photographic Canvas */}
        <div className="lg:col-span-7 h-[580px]">
          <ImageCanvas
            imageUrl={primaryImage}
            declarations={declarations}
            barcodeItems={barcodeInfo?.items || []}
            selectedFindingId={selectedFindingId}
            onSelectFinding={setSelectedFindingId}
          />
        </div>

        {/* Right Column (5 cols): Product Details & QR/Barcode Decoded Info */}
        <div className="lg:col-span-5 space-y-4">
          {/* Commodity Details Card */}
          <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-xs space-y-3">
            <h2 className="font-display font-bold text-sm text-gray-900 border-b border-gray-100 pb-2">
              Packaged Commodity Profile
            </h2>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-gray-400 block text-[11px]">Commodity / Brand</span>
                <span className="font-bold text-gray-800">{scan.product?.name || 'Unlabeled Sample'}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Category</span>
                <span className="font-bold text-gray-800">{scan.product?.category || 'Pre-packaged Food / Goods'}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Declared MRP</span>
                <span className="font-bold text-gray-800">
                  {scan.product?.mrp ? `₹ ${scan.product.mrp}` : '—'}
                </span>
              </div>
              <div>
                <span className="text-gray-400 block text-[11px]">Net Quantity</span>
                <span className="font-bold text-gray-800">{scan.product?.net_quantity || '—'}</span>
              </div>
              <div className="col-span-2">
                <span className="text-gray-400 block text-[11px]">Manufacturer / Packer</span>
                <span className="font-bold text-gray-800">{scan.product?.manufacturer_name || '—'}</span>
              </div>
            </div>
          </div>

          {/* QR & Barcode Detection Card */}
          <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-gray-100 pb-2">
              <div className="flex items-center gap-2">
                <QrCode className="w-4 h-4 text-purple-700" />
                <h2 className="font-display font-bold text-sm text-gray-900">QR & Barcode Evidence</h2>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
                {barcodeInfo?.total_detected ? `${barcodeInfo.total_detected} Detected` : 'None Detected'}
              </span>
            </div>

            {barcodeInfo?.items && barcodeInfo.items.length > 0 ? (
              <div className="space-y-2 text-xs">
                {barcodeInfo.items.map((item, idx) => (
                  <div key={idx} className="p-3 bg-purple-50/40 rounded-xl border border-purple-100 space-y-1">
                    <div className="flex items-center justify-between font-bold text-purple-950">
                      <span>{item.type} ({item.format})</span>
                      <span className="text-[10px] text-purple-700 font-mono">Conf: {(item.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="font-mono text-[11px] text-gray-700 break-all select-all">
                      {item.raw_content}
                    </div>
                    {item.is_url && item.url_safety && (
                      <div className="pt-1 flex items-center justify-between text-[10px]">
                        <span className={item.url_safety.is_safe ? 'text-emerald-700 font-bold' : 'text-red-600 font-bold'}>
                          {item.url_safety.is_safe ? 'Safe Public URL' : 'Suspicious URL Warning'}
                        </span>
                        {item.url_safety.is_safe && (
                          <a
                            href={item.raw_content}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-[#0051d5] font-bold hover:underline"
                          >
                            Visit <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400 py-2">
                No 2D QR codes or 1D retail barcodes were recognized on the photographed packaging surface.
              </p>
            )}

            <div className="p-2.5 rounded-xl bg-gray-50 text-[10px] text-gray-500 leading-tight">
              <strong>Notice:</strong> QR codes and barcodes serve as supplementary cross-checks. Decoded data does not replace required on-pack text declarations under Rule 6.
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Compliance Findings Table (Below Panels) */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="font-display font-bold text-sm text-gray-900">
              Statutory Declarations Audit & Rule Findings
            </h2>
            <p className="text-[11px] text-gray-500">
              Deterministic verification against Legal Metrology (Packaged Commodities) Rules, 2011
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-gray-50 text-gray-500 uppercase text-[10px] font-bold tracking-wider border-b border-gray-200">
              <tr>
                <th className="py-3 px-4">Mandatory Declaration</th>
                <th className="py-3 px-4">Extracted Value / Evidence</th>
                <th className="py-3 px-4">Statutory Reference</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4 text-right">Officer Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-medium text-gray-700">
              {declarations.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400 text-xs">
                    No declaration findings available for this scan.
                  </td>
                </tr>
              ) : (
                declarations.map((decl) => {
                  const isSelected = selectedFindingId === decl.id;
                  const isPass = decl.is_compliant;
                  const isReview = decl.severity === 'needs_review' || (!isPass && decl.confidence_score < 0.7);

                  let badge = (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3" /> PASS
                    </span>
                  );

                  if (isReview) {
                    badge = (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        <HelpCircle className="w-3 h-3" /> REVIEW
                      </span>
                    );
                  } else if (!isPass) {
                    badge = (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-red-50 text-red-700 border border-red-200">
                        <XCircle className="w-3 h-3" /> FAIL
                      </span>
                    );
                  }

                  return (
                    <tr
                      key={decl.id}
                      onClick={() => setSelectedFindingId(decl.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? 'bg-blue-50/70' : 'hover:bg-gray-50/80'
                      }`}
                    >
                      <td className="py-3 px-4 font-bold text-gray-900 capitalize">
                        {decl.field_type.replace('_', ' ')}
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-gray-800 max-w-[240px] truncate">
                        {decl.extracted_text || <span className="text-gray-400 italic font-sans">[Not detected on package]</span>}
                      </td>
                      <td className="py-3 px-4 text-gray-500 text-[11px] max-w-[200px] truncate">
                        {decl.rule_reference}
                      </td>
                      <td className="py-3 px-4">{badge}</td>
                      <td className="py-3 px-4 font-mono text-gray-500">
                        {(decl.confidence_score * 100).toFixed(0)}%
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => handleQuickReview(decl.id, 'confirm')}
                            title="Confirm finding"
                            className="p-1 rounded-md text-emerald-600 hover:bg-emerald-50 border border-emerald-200"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleQuickReview(decl.id, 'reject')}
                            title="Reject finding"
                            className="p-1 rounded-md text-red-600 hover:bg-red-50 border border-red-200"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingFinding(decl)}
                            title="Manual correction"
                            className="p-1 rounded-md text-[#0051d5] hover:bg-blue-50 border border-blue-200"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Immutable Audit Trail Section */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs p-5 space-y-3">
        <div className="flex items-center gap-2 border-b border-gray-100 pb-2">
          <History className="w-4 h-4 text-gray-500" />
          <h2 className="font-display font-bold text-sm text-gray-900">Inspection Audit Trail</h2>
        </div>
        <div className="space-y-2 text-xs">
          {auditLogs.length === 0 ? (
            <p className="text-gray-400 py-2">No audit records logged yet.</p>
          ) : (
            auditLogs.map((log) => (
              <div key={log.id} className="p-2.5 rounded-xl bg-gray-50 border border-gray-200 flex items-center justify-between">
                <div>
                  <span className="font-bold text-gray-900">{log.action}</span>
                  <span className="text-gray-500 ml-2 font-mono text-[11px]">
                    {log.metadata ? JSON.stringify(log.metadata) : ''}
                  </span>
                </div>
                <span className="text-[10px] text-gray-400 whitespace-nowrap">
                  {new Date(log.created_at).toLocaleString('en-IN')}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Declaration Editor Modal */}
      {editingFinding && (
        <DeclarationEditorModal
          finding={editingFinding}
          isOpen={!!editingFinding}
          onClose={() => setEditingFinding(null)}
          onSave={handleSaveCorrection}
        />
      )}
    </div>
  );
};
