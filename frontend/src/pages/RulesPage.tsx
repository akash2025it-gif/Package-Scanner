import React, { useState } from 'react';
import { BookOpen, ShieldCheck, Scale, Ruler, AlertCircle, Calculator, CheckCircle2, Sparkles } from 'lucide-react';

export const RulesPage: React.FC = () => {
  const [calcQty, setCalcQty] = useState<number>(200);
  const [calcUnit, setCalcUnit] = useState<'g' | 'ml'>('g');
  const [isBlown, setIsBlown] = useState<boolean>(false);

  const calculateRequiredFont = (qty: number, blown: boolean) => {
    if (qty <= 50) return { minMm: blown ? 2.0 : 1.0, slab: 'Up to 50 g / 50 ml' };
    if (qty <= 100) return { minMm: blown ? 3.0 : 1.5, slab: 'Above 50 up to 100 g / ml' };
    if (qty <= 200) return { minMm: blown ? 4.0 : 2.0, slab: 'Above 100 up to 200 g / ml' };
    if (qty <= 500) return { minMm: blown ? 8.0 : 4.0, slab: 'Above 200 up to 500 g / ml' };
    return { minMm: blown ? 12.0 : 6.0, slab: 'Above 500 g / 500 ml' };
  };

  const fontResult = calculateRequiredFont(calcQty, isBlown);

  const rules = [
    {
      id: 'Rule 6(1)(a)',
      title: 'Generic or Common Name',
      severity: 'Critical',
      description: 'The common or generic name of the commodity contained in the package must be prominently declared.',
      conditions: 'Must not use misleading brand names alone without declaring what the product actually is.',
      exception: 'Standard agricultural raw commodities where container clearly reveals contents.',
    },
    {
      id: 'Rule 6(1)(b)',
      title: 'Manufacturer / Packer / Importer Details',
      severity: 'Critical',
      description: 'Name and complete address of the manufacturer, or packer, or importer must be clearly declared.',
      conditions: 'Street name, city, state, and pin code must be visible to identify legal liability.',
      exception: 'None. Mandatory on all pre-packaged goods sold in India.',
    },
    {
      id: 'Rule 6(1)(c)',
      title: 'Country of Origin',
      severity: 'Critical',
      description: 'For imported goods, the country of origin or manufacturer country must be conspicuously declared.',
      conditions: 'Phrases such as "Made in [Country]", "Country of Origin: [Country]" required.',
      exception: 'Domestically manufactured goods where Indian manufacturer address is fully declared.',
    },
    {
      id: 'Rule 6(1)(d) & Rule 8',
      title: 'Net Quantity Declarations',
      severity: 'Critical',
      description: 'Net quantity must be declared in terms of standard unit of weight, measure, or number.',
      conditions: 'Only standard SI symbols (g, kg, ml, l, N). Symbols with plural "s" (gms, kgs, ltrs) are illegal.',
      exception: 'Packages containing less than 10g or 10ml, subject to exemption provisions.',
    },
    {
      id: 'Rule 6(1)(e)',
      title: 'Month and Year of Manufacture / Packing',
      severity: 'Major',
      description: 'The month and year in which the commodity is manufactured or pre-packed or imported.',
      conditions: 'Format: MM/YYYY, Month YYYY, or DD/MM/YYYY.',
      exception: 'Commodities exempted under specific agricultural or bulk packaging rules.',
    },
    {
      id: 'Rule 6(1)(f)',
      title: 'Maximum Retail Price (MRP) & Tax Inclusivity',
      severity: 'Critical',
      description: 'MRP in Indian Rupees inclusive of all taxes must be declared prominently.',
      conditions: 'Must include ₹ or Rs. symbol, followed by "Inclusive of all taxes" or "(Incl. of all taxes)".',
      exception: 'None. Selling above declared MRP is an offense under Section 36 of the Legal Metrology Act, 2009.',
    },
    {
      id: 'Rule 6(1)(g)',
      title: 'Unit Sale Price (USP)',
      severity: 'Major',
      description: 'Unit sale price rounded off to the nearest two decimal places per g/kg/ml/l/unit.',
      conditions: 'Mandatory where package quantity exceeds 1kg or 1 litre.',
      exception: 'Packages containing commodities under standard unitary weight.',
    },
    {
      id: 'Rule 6(1)(h)',
      title: 'Consumer Care Redressal',
      severity: 'Major',
      description: 'Name, address, telephone number, and email of person or office to be contacted for consumer grievances.',
      conditions: 'Working telephone number and valid email address must be declared on consumer panel.',
      exception: 'None.',
    },
  ];

  const fontSlabs = [
    { netQty: 'Up to 50 g / 50 ml', normalMm: '1.0 mm', blownMm: '2.0 mm' },
    { netQty: 'Above 50 g / ml up to 100 g / ml', normalMm: '1.5 mm', blownMm: '3.0 mm' },
    { netQty: 'Above 100 g / ml up to 200 g / ml', normalMm: '2.0 mm', blownMm: '4.0 mm' },
    { netQty: 'Above 200 g / ml up to 500 g / ml', normalMm: '4.0 mm', blownMm: '8.0 mm' },
    { netQty: 'Above 500 g / ml', normalMm: '6.0 mm', blownMm: '12.0 mm' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-blue-50 text-[#0051d5] border border-blue-200">
            Statutory Codex
          </span>
        </div>
        <h1 className="font-display font-black text-2xl sm:text-3xl text-slate-900 tracking-tight mt-1">
          Legal Metrology Rules & Standards
        </h1>
        <p className="text-xs text-slate-500 mt-1 max-w-2xl leading-relaxed">
          Official statutory guidelines under Legal Metrology (Packaged Commodities) Rules, 2011, Second Schedule font height slabs, and SI unit standards.
        </p>
      </div>

      {/* Interactive Minimum Font Size Calculator Widget */}
      <div className="bg-gradient-to-r from-blue-50/90 via-indigo-50/70 to-blue-50 rounded-3xl border border-blue-200/80 p-6 shadow-2xs space-y-4">
        <div className="flex items-center gap-2.5 border-b border-blue-200/60 pb-3">
          <div className="w-8 h-8 rounded-xl bg-[#0051d5] text-white flex items-center justify-center shadow-xs">
            <Calculator className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-display font-bold text-sm text-slate-900">
              Interactive Statutory Font Height Calculator
            </h2>
            <p className="text-[11px] text-slate-600">
              Calculate mandatory numeral height in mm under Rule 7 & Second Schedule based on package net quantity
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 text-xs items-end">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Declared Net Quantity</label>
            <input
              type="number"
              min={1}
              value={calcQty}
              onChange={(e) => setCalcQty(Math.max(1, Number(e.target.value) || 1))}
              className="w-full rounded-xl border border-slate-300 p-2.5 text-xs bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:outline-none"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Quantity Unit</label>
            <select
              value={calcUnit}
              onChange={(e) => setCalcUnit(e.target.value as any)}
              className="w-full rounded-xl border border-slate-300 p-2.5 text-xs bg-white focus:ring-2 focus:ring-[#0051d5]/20 focus:outline-none font-bold"
            >
              <option value="g">Grams (g)</option>
              <option value="ml">Millilitres (ml)</option>
            </select>
          </div>

          <div className="flex items-center gap-2 p-2.5 bg-white rounded-xl border border-slate-200">
            <input
              type="checkbox"
              id="blownCheck"
              checked={isBlown}
              onChange={(e) => setIsBlown(e.target.checked)}
              className="rounded text-[#0051d5] focus:ring-[#0051d5]"
            />
            <label htmlFor="blownCheck" className="text-xs font-semibold text-slate-700 cursor-pointer">
              Blown / Moulded Surface
            </label>
          </div>

          <div className="p-3 bg-white rounded-2xl border border-blue-200 text-center shadow-xs">
            <span className="text-[10px] text-slate-400 uppercase font-bold block">Mandatory Min Height</span>
            <span className="font-display font-black text-2xl text-[#0051d5]">
              {fontResult.minMm} mm
            </span>
            <span className="text-[10px] text-slate-500 block truncate">({fontResult.slab})</span>
          </div>
        </div>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.map((rule, idx) => (
          <div key={idx} className="bg-white rounded-3xl p-5 border border-slate-200/90 shadow-2xs space-y-3">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <span className="font-mono text-xs font-bold text-[#0051d5]">{rule.id}</span>
              <span
                className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                  rule.severity === 'Critical'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                {rule.severity} Mandate
              </span>
            </div>

            <h3 className="font-display font-bold text-sm text-slate-900">{rule.title}</h3>
            <p className="text-xs text-slate-600 leading-relaxed">{rule.description}</p>

            <div className="p-3 rounded-2xl bg-slate-50 text-[11px] space-y-1 border border-slate-200/80">
              <div>
                <strong className="text-slate-800">Verification Condition:</strong>{' '}
                <span className="text-slate-600">{rule.conditions}</span>
              </div>
              <div>
                <strong className="text-slate-800">Exemption Scope:</strong>{' '}
                <span className="text-slate-500">{rule.exception}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Second Schedule Minimum Font Size Slabs Table */}
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
        <div>
          <h2 className="font-display font-bold text-sm text-slate-900">
            Second Schedule – Minimum Height of Numerals & Letters (Rule 7 & 9)
          </h2>
          <p className="text-[11px] text-slate-500">
            Statutory minimum font height requirements corresponding to net quantity packaging weight and container type.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border border-slate-200 rounded-2xl overflow-hidden">
            <thead className="bg-slate-50 text-[10px] font-bold uppercase text-slate-600">
              <tr>
                <th className="p-3.5 border-b border-r border-slate-200">Net Quantity Category</th>
                <th className="p-3.5 border-b border-r border-slate-200">Normal Containers / Labels (mm)</th>
                <th className="p-3.5 border-b border-slate-200">Blown / Formed / Moulded Containers (mm)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {fontSlabs.map((slab, i) => (
                <tr key={i} className="hover:bg-slate-50/80 transition-colors">
                  <td className="p-3.5 border-r border-slate-200 font-semibold text-slate-900">{slab.netQty}</td>
                  <td className="p-3.5 border-r border-slate-200 font-mono text-[#0051d5] font-bold">{slab.normalMm}</td>
                  <td className="p-3.5 font-mono text-purple-700 font-bold">{slab.blownMm}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200 text-[11px] text-amber-900 leading-relaxed flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 text-amber-700 shrink-0" />
          <span>
            <strong>Scientific Calibration Notice:</strong> Automated 2D camera pixel measurement provides statutory estimation. Formal legal proceedings require certified physical scale verification by an authorized Legal Metrology Officer.
          </span>
        </div>
      </div>
    </div>
  );
};
