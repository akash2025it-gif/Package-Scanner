import React, { useState, useRef } from 'react';
import { ZoomIn, ZoomOut, RotateCcw, Eye, EyeOff, QrCode } from 'lucide-react';
import { BoundingBox, BarcodeItem, DeclarationFinding } from '../../types';

interface ImageCanvasProps {
  imageUrl: string;
  declarations: DeclarationFinding[];
  barcodeItems?: BarcodeItem[];
  selectedFindingId?: string | null;
  onSelectFinding?: (id: string | null) => void;
}

export const ImageCanvas: React.FC<ImageCanvasProps> = ({
  imageUrl,
  declarations,
  barcodeItems = [],
  selectedFindingId,
  onSelectFinding,
}) => {
  const [zoom, setZoom] = useState<number>(1.0);
  const [showOcrBoxes, setShowOcrBoxes] = useState<boolean>(true);
  const [showBarcodes, setShowBarcodes] = useState<boolean>(true);
  const imgRef = useRef<HTMLImageElement>(null);

  const handleZoom = (delta: number) => {
    setZoom((prev) => Math.max(0.6, Math.min(3.5, prev + delta)));
  };

  const resetZoom = () => {
    setZoom(1.0);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">
      {/* Canvas Toolbar */}
      <div className="p-3 bg-gray-50 border-b border-gray-200 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-gray-700">
          <span>Inspection Photographic Evidence</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Layer toggles */}
          <button
            type="button"
            onClick={() => setShowOcrBoxes((v) => !v)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium flex items-center gap-1 transition-colors ${
              showOcrBoxes ? 'bg-blue-50 border-blue-200 text-[#0051d5]' : 'bg-white border-gray-200 text-gray-600'
            }`}
          >
            {showOcrBoxes ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            OCR Boxes
          </button>

          <button
            type="button"
            onClick={() => setShowBarcodes((v) => !v)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium flex items-center gap-1 transition-colors ${
              showBarcodes ? 'bg-purple-50 border-purple-200 text-purple-700' : 'bg-white border-gray-200 text-gray-600'
            }`}
          >
            <QrCode className="w-3.5 h-3.5" />
            QR / Barcode
          </button>

          <div className="h-4 w-px bg-gray-300 mx-1" />

          {/* Zoom controls */}
          <button
            type="button"
            onClick={() => handleZoom(-0.25)}
            className="p-1.5 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 text-gray-700"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-gray-500 font-mono text-[11px] w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            onClick={() => handleZoom(0.25)}
            className="p-1.5 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 text-gray-700"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={resetZoom}
            className="p-1.5 rounded-lg bg-white border border-gray-200 hover:bg-gray-100 text-gray-700"
            title="Reset Zoom"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Interactive Viewport */}
      <div className="flex-1 overflow-auto bg-gray-900/5 p-4 flex items-center justify-center min-h-[420px]">
        <div
          className="relative inline-block transition-transform duration-100 origin-center select-none shadow-md rounded-lg overflow-hidden bg-white"
          style={{ transform: `scale(${zoom})` }}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt="Packaged Commodity"
            className="block max-w-full max-h-[68vh] object-contain"
          />

          {/* OCR Bounding Boxes */}
          {showOcrBoxes &&
            declarations.map((decl) => {
              const bbox = decl.bounding_box;
              if (!bbox || (!bbox.w && !bbox.width) || (!bbox.h && !bbox.height)) return null;

              const isSelected = selectedFindingId === decl.id;
              const isPass = decl.is_compliant;
              const isReview = decl.severity === 'needs_review' || (!isPass && decl.confidence_score < 0.7);

              let borderColor = 'border-emerald-500 bg-emerald-500/10 text-emerald-900';
              if (isReview) {
                borderColor = 'border-amber-500 bg-amber-500/15 text-amber-900';
              } else if (!isPass) {
                borderColor = 'border-red-500 bg-red-500/15 text-red-900';
              }

              if (isSelected) {
                borderColor += ' ring-2 ring-blue-600 ring-offset-1 z-20';
              }

              return (
                <div
                  key={decl.id}
                  onClick={() => onSelectFinding?.(decl.id)}
                  className={`absolute border-2 rounded-xs cursor-pointer transition-all hover:opacity-100 ${borderColor}`}
                  style={{
                    left: `${bbox.x}px`,
                    top: `${bbox.y}px`,
                    width: `${bbox.w || bbox.width}px`,
                    height: `${bbox.h || bbox.height}px`,
                  }}
                  title={`${decl.field_type}: ${decl.extracted_text || '[Not detected]'}`}
                >
                  <span className="absolute -top-4 left-0 text-[9px] font-bold px-1 rounded-xs bg-white/90 shadow-xs border border-gray-300 truncate max-w-[120px]">
                    {decl.field_type}
                  </span>
                </div>
              );
            })}

          {/* Barcode & QR code bounding overlays */}
          {showBarcodes &&
            barcodeItems.map((item, idx) => {
              const bbox = item.bounding_box;
              if (!bbox || (!bbox.w && !bbox.width)) return null;

              return (
                <div
                  key={idx}
                  className="absolute border-2 border-purple-600 bg-purple-500/20 rounded-xs z-15"
                  style={{
                    left: `${bbox.x}px`,
                    top: `${bbox.y}px`,
                    width: `${bbox.w || bbox.width}px`,
                    height: `${bbox.h || bbox.height}px`,
                  }}
                  title={`${item.type}: ${item.raw_content}`}
                >
                  <span className="absolute -top-4 left-0 text-[9px] font-bold px-1 rounded-xs bg-purple-700 text-white shadow-xs">
                    {item.type}
                  </span>
                </div>
              );
            })}
        </div>
      </div>

      {/* Legend Footer */}
      <div className="p-2.5 bg-white border-t border-gray-200 flex flex-wrap items-center justify-between text-[11px] text-gray-500 gap-2">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Compliant
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Non-Compliant
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Requires Review
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span> QR / Barcode
          </span>
        </div>
        <span className="text-[10px] text-gray-400">Click any bounding box to jump to declaration details</span>
      </div>
    </div>
  );
};
