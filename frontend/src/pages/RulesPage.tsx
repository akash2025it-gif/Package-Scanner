import React from 'react';
import { BookOpen, ShieldCheck, Scale, Ruler, AlertCircle } from 'lucide-react';

export const RulesPage: React.FC = () => {
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
      <div>
        <h1 className="font-display font-extrabold text-xl sm:text-2xl text-gray-900 tracking-tight">
          Legal Metrology Rules & Standards
        </h1>
        <p className="text-xs text-gray-500 mt-1">
          Official statutory guidelines under Legal Metrology (Packaged Commodities) Rules, 2011 and official amendments.
        </p>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.map((rule, idx) => (
          <div key={idx} className="bg-white rounded-2xl p-5 border border-gray-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between border-b border-gray-100 pb-2">
              <span className="font-mono text-xs font-bold text-[#0051d5]">{rule.id}</span>
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                  rule.severity === 'Critical'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                {rule.severity} Mandate
              </span>
            </div>

            <h3 className="font-display font-bold text-sm text-gray-900">{rule.title}</h3>
            <p className="text-xs text-gray-600 leading-relaxed">{rule.description}</p>

            <div className="p-3 rounded-xl bg-gray-50 text-[11px] space-y-1">
              <div>
                <strong className="text-gray-700">Verification Condition:</strong>{' '}
                <span className="text-gray-600">{rule.conditions}</span>
              </div>
              <div>
                <strong className="text-gray-700">Exemption Scope:</strong>{' '}
                <span className="text-gray-500">{rule.exception}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Second Schedule Minimum Font Size Slabs Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xs p-6 space-y-4">
        <div>
          <h2 className="font-display font-bold text-sm text-gray-900">
            Second Schedule – Minimum Height of Numerals & Letters (Rule 7 & 9)
          </h2>
          <p className="text-[11px] text-gray-500">
            Statutory minimum font height requirements corresponding to net quantity packaging weight and container type.
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border border-gray-200">
            <thead className="bg-gray-100 text-[10px] font-bold uppercase text-gray-600">
              <tr>
                <th className="p-3 border">Net Quantity Category</th>
                <th className="p-3 border">Normal Containers / Labels (mm)</th>
                <th className="p-3 border">Blown / Formed / Moulded Containers (mm)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 font-medium text-gray-700">
              {fontSlabs.map((slab, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="p-3 border font-semibold text-gray-900">{slab.netQty}</td>
                  <td className="p-3 border font-mono text-[#0051d5] font-bold">{slab.normalMm}</td>
                  <td className="p-3 border font-mono text-purple-700 font-bold">{slab.blownMm}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="p-3 rounded-xl bg-amber-50/70 border border-amber-200 text-[11px] text-amber-900 leading-relaxed flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-700 shrink-0" />
          <span>
            <strong>Scientific Calibration Disclaimer:</strong> Automatic 2D camera pixel measurement of font height is an estimation aid. Official enforcement proceedings require certified physical scale calibration.
          </span>
        </div>
      </div>
    </div>
  );
};
