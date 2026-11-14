import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { Scan } from '../types';
import {
  ShieldAlert,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  QrCode,
  ScanText,
  FileCheck2,
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
    { title: 'Threshold Automation & Audit Trail', desc: 'High-confidence confirmation & inspector routing', icon: ShieldAlert },
  ];

  return (
    <div className="max-w-xl mx-auto py-12 px-4 text-center space-y-8">
      <div>
        <div className="w-14 h-14 rounded-2xl bg-[#0051d5] text-white flex items-center justify-center mx-auto shadow-lg animate-pulse">
          <ScanText className="w-7 h-7" />
        </div>
        <h1 className="mt-4 font-display font-extrabold text-xl text-gray-900 tracking-tight">
          Analyzing Packaging Commodity
        </h1>
        <p className="text-xs text-gray-500 mt-1 font-mono">
          Inspection ID: {id}
        </p>
      </div>

      {error ? (
        <div className="p-5 rounded-2xl bg-red-50 border border-red-200 text-red-700 text-xs space-y-3 text-left">
          <div className="flex items-center gap-2 font-bold">
            <AlertTriangle className="w-4 h-4" />
            <span>Inspection Analysis Halted</span>
          </div>
          <p>{error}</p>
          <button
            onClick={() => navigate(`/scan/${id}`)}
            className="px-4 py-2 bg-red-600 text-white rounded-xl text-xs font-semibold"
          >
            Inspect Scan Record Anyway
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-6 border border-gray-200 shadow-xs text-left space-y-4">
          <div className="space-y-4">
            {steps.map((step, idx) => {
              const stepNum = idx + 1;
              const isDone = currentStep > stepNum;
              const isCurrent = currentStep === stepNum;
              const Icon = step.icon;

              return (
                <div key={idx} className="flex items-start gap-3.5">
                  <div
                    className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 text-xs font-bold transition-all ${
                      isDone
                        ? 'bg-emerald-100 text-emerald-700'
                        : isCurrent
                        ? 'bg-blue-100 text-[#0051d5] ring-2 ring-blue-400 ring-offset-1 animate-pulse'
                        : 'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                  </div>
                  <div>
                    <div
                      className={`text-xs font-bold ${
                        isCurrent ? 'text-gray-900' : isDone ? 'text-gray-700' : 'text-gray-400'
                      }`}
                    >
                      {step.title}
                    </div>
                    <div className="text-[11px] text-gray-400">{step.desc}</div>
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
