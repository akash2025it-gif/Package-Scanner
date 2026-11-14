import React, { useState } from 'react';
import { X, CheckCircle, AlertTriangle, XCircle, RotateCcw } from 'lucide-react';
import { DeclarationFinding } from '../../types';

interface DeclarationEditorModalProps {
  finding: DeclarationFinding;
  isOpen: boolean;
  onClose: () => void;
  onSave: (payload: { extracted_text?: string; is_compliant?: boolean; notes?: string }) => Promise<void>;
}

export const DeclarationEditorModal: React.FC<DeclarationEditorModalProps> = ({
  finding,
  isOpen,
  onClose,
  onSave,
}) => {
  const [text, setText] = useState<string>(finding.extracted_text || '');
  const [status, setStatus] = useState<string>(
    finding.is_compliant ? 'compliant' : finding.severity === 'needs_review' ? 'needs_review' : 'non_compliant'
  );
  const [notes, setNotes] = useState<string>(finding.reviewer_notes || '');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError('Please provide officer review notes explaining your determination.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSave({
        extracted_text: text,
        is_compliant: status === 'compliant',
        notes: notes.trim(),
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update declaration');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-gray-200 overflow-hidden">
        <div className="p-4 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h3 className="font-display font-bold text-sm text-gray-900">
              Inspector Review & Override: {finding.field_type}
            </h3>
            <p className="text-[11px] text-gray-500">{finding.rule_reference}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
              {error}
            </div>
          )}

          <div>
            <label className="block font-semibold text-gray-700 mb-1">Extracted Text Value</label>
            <textarea
              rows={2}
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="w-full rounded-xl border border-gray-300 p-2.5 text-xs focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
              placeholder="Declared text on physical packaging..."
            />
          </div>

          <div>
            <label className="block font-semibold text-gray-700 mb-1">Compliance Determination</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full rounded-xl border border-gray-300 p-2.5 text-xs bg-white focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
            >
              <option value="compliant">COMPLIANT (Evidence meets statutory criteria)</option>
              <option value="non_compliant">NON-COMPLIANT (Confirmed statutory violation)</option>
              <option value="needs_review">NEEDS MANUAL REVIEW (Requires physical lab measurement)</option>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-gray-700 mb-1">
              Officer Audit Notes <span className="text-red-500">*</span>
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Record justification (e.g. 'Physically verified with calibrated micrometer on back panel', 'Tax inclusion statement confirmed on side flap')..."
              className="w-full rounded-xl border border-gray-300 p-2.5 text-xs focus:ring-2 focus:ring-[#0051d5] focus:outline-none"
              required
            />
          </div>

          <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200 text-[11px] text-blue-900 leading-relaxed">
            <span className="font-bold">Statutory Integrity Notice:</span> All inspector determinations are logged with officer timestamp and credentials into the immutable audit trail.
          </div>

          <div className="pt-2 flex items-center justify-end gap-2 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl border border-gray-300 text-gray-700 font-semibold hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl bg-[#0051d5] hover:bg-[#003ea7] text-white font-semibold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              {isSubmitting ? 'Saving Determination...' : 'Confirm Determination'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
