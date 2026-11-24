import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Scan } from '../types';
import {
  ShieldCheck,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  QrCode,
  ScanText,
  FileCheck2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';

export const ScanProcessingPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [scan, setScan] = useState<Scan | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let pollCount = 0;
    const interval = setInterval(async () => {
      pollCount++;
      try {
        const data = await api.getScan(id);
        setScan(data);

        // Advance steps visually
        if (pollCount > 1) setCurrentStep(2);
        if (pollCount > 3) setCurrentStep(3);
        if (pollCount > 4) setCurrentStep(4);
        if (pollCount > 6) setCurrentStep(5);

        if (data.status !== 'processing' || data.declarations?.length > 0) {
          clearInterval(interval);
          setCurrentStep(6);
          setTimeout(() => {
            navigate(`/scan/${id}`);
          }, 1000);
        }
      } catch (err: any) {
        clearInterval(interval);
        setError(err.message || 'Failed to poll scan analysis status');
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [id, navigate]);

  const steps = [
    { title: 'Image Quality & Blur Validation', desc: 'Laplacian variance sharpness verification', icon: CheckCircle2 },
    { title: 'QR Code & Barcode Decoding', desc: 'OpenCV detector for EAN/UPC & QR validation', icon: QrCode },
    { title: 'Label Preprocessing & Deskewing', desc: 'CLAHE contrast enhancement and angle correction', icon: RotateCcw },
    { title: 'OCR & Bounding Box Extraction', desc: 'Extracting words, layout blocks, and confidence', icon: ScanText },
    { title: 'LMPC 2011 Legal Rule Engine', desc: 'Rule 6 mandatory declarations and font slabs', icon: FileCheck2 },
    { title: 'Threshold Automation & Audit Trail', desc: 'High-confidence confirmation & inspector routing', icon: ShieldCheck },
  ];

  return (
    <div className="max-w-xl mx-auto py-12 px-4 text-center space-y-8">
      <div>
        <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-[#00174b] to-[#0051d5] text-white flex items-center justify-center mx-auto shadow-xl shadow-blue-900/20 ring-1 ring-white/20 animate-pulse">
          <ScanText className="w-8 h-8 text-white" />
        </div>
        <h1 className="mt-4 font-display font-black text-2xl text-slate-900 tracking-tight">
          Analyzing Packaging Commodity
        </h1>
        <p className="text-xs text-slate-500 mt-1 font-mono">
          Inspection Dossier ID: {id}
        </p>
      </div>

      {error ? (
        <div className="p-6 rounded-3xl bg-red-50 border border-red-200 text-red-700 text-xs space-y-3 text-left shadow-2xs">
          <div className="flex items-center gap-2 font-bold text-sm text-red-800">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span>Inspection Analysis Halted</span>
          </div>
          <p className="leading-relaxed">{error}</p>
          <button
            onClick={() => navigate(`/scan/${id}`)}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-bold transition-colors cursor-pointer"
          >
            Inspect Scan Record Anyway
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-2xs text-left space-y-4">
          <div className="space-y-4">
            {steps.map((step, idx) => {
              const stepNum = idx + 1;
              const isDone = currentStep > stepNum;
              const isCurrent = currentStep === stepNum;
              const Icon = step.icon;

              return (
                <div key={idx} className="flex items-start gap-3.5">
                  <div
                    className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 transition-colors shadow-2xs ${
                      isDone
                        ? 'bg-emerald-100 text-emerald-700'
                        : isCurrent
                        ? 'bg-[#0051d5] text-white animate-pulse'
                        : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {isCurrent ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>
                  <div>
                    <span
                      className={`font-bold text-xs block ${
                        isDone
                          ? 'text-emerald-900'
                          : isCurrent
                          ? 'text-[#0051d5]'
                          : 'text-slate-400'
                      }`}
                    >
                      {step.title}
                    </span>
                    <span className="text-[11px] text-slate-500 leading-snug block">
                      {step.desc}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
