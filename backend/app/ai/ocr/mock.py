import re
from typing import Any, Dict, Optional
from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock


class MockOCRProvider(OCRProvider):
    """
    Deterministic & Dynamic Mock OCR Provider for tests, demo environments, and offline runs.
    Extracts text dynamically for any packaged commodity (Dry fruits, Biscuits, Chips, Rice, Flour, Spices, Beverages, etc.)
    using CURRENT scan product data without hardcoded static overrides.
    """

    def __init__(self, sample_scenario: str = "packaged_commodity"):
        self.sample_scenario = sample_scenario

    async def extract_text(
        self,
        image_bytes: bytes,
        product_info: Optional[Dict[str, Any]] = None,
        image_width: int = 1000,
        image_height: int = 1000,
        **kwargs,
    ) -> OCRResult:
        w = float(image_width) if image_width > 0 else 1000.0
        h = float(image_height) if image_height > 0 else 1000.0

        p_info = product_info or {}
        p_name = (p_info.get("name") or "").strip() or "Packaged Commodity"
        p_brand = (p_info.get("brand") or "").strip() or "Standard Brand"
        p_cat = (p_info.get("category") or "").strip() or "Packaged Food"
        p_mfg_name = (p_info.get("manufacturer_name") or "").strip()
        p_mfg_addr = (p_info.get("manufacturer_address") or "").strip()
        p_origin = (p_info.get("country_of_origin") or "").strip() or "India"

        name_lower = p_name.lower()
        cat_lower = p_cat.lower()
        brand_lower = p_brand.lower()

        # Determine generic / common name dynamically
        if "almond" in name_lower or "almond" in cat_lower:
            common_name = "California Almonds (Dry Fruits)"
        elif "cashew" in name_lower or "cashew" in cat_lower:
            common_name = "Whole Cashew Nuts (Dry Fruits)"
        elif "walnut" in name_lower or "walnut" in cat_lower:
            common_name = "Inshell Walnuts (Dry Fruits)"
        elif "raisin" in name_lower or "raisin" in cat_lower:
            common_name = "Golden Raisins (Dry Fruits)"
        elif "dry fruit" in name_lower or "dry fruit" in cat_lower:
            common_name = "Assorted Dry Fruits"
        elif "chips" in name_lower or "chips" in cat_lower:
            common_name = "Potato Chips"
        elif "biscuit" in name_lower or "cookie" in name_lower or "biscuit" in cat_lower:
            common_name = "Biscuits & Cookies"
        elif "rice" in name_lower or "rice" in cat_lower:
            common_name = "Basmati Rice"
        elif "atta" in name_lower or "flour" in name_lower or "flour" in cat_lower:
            common_name = "Whole Wheat Atta"
        elif "spice" in name_lower or "masala" in name_lower or "spices" in cat_lower:
            common_name = "Blended Spices"
        elif "tea" in name_lower or "tea" in cat_lower:
            common_name = "Black Tea"
        elif "coffee" in name_lower or "coffee" in cat_lower:
            common_name = "Pure Coffee"
        elif "oil" in name_lower or "oil" in cat_lower:
            common_name = "Refined Edible Oil"
        elif "juice" in name_lower or "beverage" in cat_lower:
            common_name = "Fruit Juice Beverage"
        elif "shampoo" in name_lower or "shampoo" in cat_lower:
            common_name = "Hair Cleanser (Shampoo)"
        elif "soap" in name_lower or "soap" in cat_lower:
            common_name = "Toilet Soap"
        elif "snack" in name_lower or "snack" in cat_lower:
            common_name = "Extruded Savory Snack"
        else:
            common_name = p_name

        # Determine net quantity
        qty_match = re.search(r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l|mg|L|mL|N|pcs|units)\b", p_name, re.IGNORECASE)
        if qty_match:
            qty_num = float(qty_match.group(1))
            qty_unit = qty_match.group(2).strip()
            qty_str = f"{int(qty_num) if qty_num.is_integer() else qty_num} {qty_unit}"
        elif "chips" in name_lower or "snack" in name_lower:
            qty_num = 50.0
            qty_unit = "g"
            qty_str = "50 g"
        elif "oil" in name_lower:
            qty_num = 1.0
            qty_unit = "L"
            qty_str = "1 L"
        elif "atta" in name_lower or "rice" in name_lower:
            qty_num = 5.0
            qty_unit = "kg"
            qty_str = "5 kg"
        elif "shampoo" in name_lower:
            qty_num = 650.0
            qty_unit = "ml"
            qty_str = "650 ml"
        elif "biscuit" in name_lower:
            qty_num = 150.0
            qty_unit = "g"
            qty_str = "150 g"
        elif "dry fruit" in name_lower or "almond" in name_lower or "cashew" in name_lower:
            qty_num = 250.0
            qty_unit = "g"
            qty_str = "250 g"
        elif "tea" in name_lower or "coffee" in name_lower:
            qty_num = 250.0
            qty_unit = "g"
            qty_str = "250 g"
        else:
            qty_num = 100.0
            qty_unit = "g"
            qty_str = "100 g"

        # Determine MRP and Unit Sale Price dynamically
        if "chips" in name_lower or "snack" in name_lower:
            mrp_val = 20.0
            usp_val = mrp_val / qty_num if qty_num > 0 else 0.40
            usp_unit = qty_unit
        elif "dry fruit" in name_lower or "almond" in name_lower or "cashew" in name_lower:
            mrp_val = 299.0
            usp_val = mrp_val / qty_num if qty_num > 0 else 1.20
            usp_unit = qty_unit
        elif "biscuit" in name_lower:
            mrp_val = 30.0
            usp_val = mrp_val / qty_num if qty_num > 0 else 0.20
            usp_unit = qty_unit
        elif "atta" in name_lower or "rice" in name_lower:
            mrp_val = 245.0
            usp_val = mrp_val / (qty_num if qty_unit == "kg" else qty_num / 1000.0)
            usp_unit = "kg"
        elif "oil" in name_lower:
            mrp_val = 155.0
            usp_val = 155.0
            usp_unit = "L"
        elif "tea" in name_lower or "coffee" in name_lower:
            mrp_val = 140.0
            usp_val = mrp_val / qty_num if qty_num > 0 else 0.56
            usp_unit = qty_unit
        else:
            mrp_val = 99.0
            usp_val = mrp_val / qty_num if qty_num > 0 else 0.99
            usp_unit = qty_unit

        mrp_str = f"MRP ₹ {mrp_val:.2f} (inclusive of all taxes)"
        usp_str = f"Unit Sale Price: ₹ {usp_val:.2f} / {usp_unit}"

        # Determine Manufacturer
        if p_mfg_name and p_mfg_addr:
            mfg_text = f"Manufactured & Packed by: {p_mfg_name}, {p_mfg_addr}"
        elif p_mfg_name:
            mfg_text = f"Manufactured & Packed by: {p_mfg_name}, Industrial Area, New Delhi - 110020. Lic. No. 10019011000456"
        elif "lay" in brand_lower or "pepsico" in brand_lower or "kurkure" in brand_lower or "lay" in name_lower:
            mfg_text = "Manufactured & Packed by: PepsiCo India Holdings Pvt. Ltd., Level 3-5, Pioneer Square, Sector 62, Near Golf Course Ext. Road, Gurugram - 122101, Haryana. Lic. No. 10014064000435"
        elif "parle" in brand_lower or "parle" in name_lower:
            mfg_text = "Manufactured & Packed by: Parle Products Pvt. Ltd., V.S. Khandekar Marg, Vile Parle East, Mumbai - 400057, Maharashtra. Lic. No. 10012022000088"
        elif "fortune" in brand_lower or "adani" in brand_lower:
            mfg_text = "Manufactured & Packed by: Adani Wilmar Limited, Fortune House, Near Navrangpura Railway Crossing, Ahmedabad - 380009, Gujarat. Lic. No. 10013021000853"
        elif "aashirvaad" in brand_lower or "sunfeast" in brand_lower or "bingo" in brand_lower:
            mfg_text = "Manufactured & Packed by: ITC Limited, 37, J.L. Nehru Road, Kolkata - 700071, West Bengal. Lic. No. 10012031000012"
        else:
            clean_brand = p_brand if p_brand else "PackCheck"
            mfg_text = f"Manufactured & Packed by: {clean_brand} Consumer Products Pvt. Ltd., Plot No. 42, Sector 18, Industrial Estate, Gurugram - 122015, Haryana. Lic. No. 10019011000888"

        brand_slug = re.sub(r"[^a-zA-Z0-9]", "", brand_lower) or "support"
        care_text = f"Consumer Care: Executive, {p_brand} Consumer Care Cell, Toll Free: 1800-222-4444, Email: care@{brand_slug}.com"

        blocks = [
            TextBlock(
                text=f"{p_brand.upper()} {p_name.upper()}",
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.08, 1), "w": round(w * 0.80, 1), "h": round(h * 0.07, 1)},
                confidence=0.98,
                font_size_px=round(h * 0.045, 1),
            ),
            TextBlock(
                text=common_name,
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.16, 1), "w": round(w * 0.65, 1), "h": round(h * 0.05, 1)},
                confidence=0.96,
                font_size_px=round(h * 0.032, 1),
            ),
            TextBlock(
                text=f"Net Quantity: {qty_str}",
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.23, 1), "w": round(w * 0.50, 1), "h": round(h * 0.055, 1)},
                confidence=0.97,
                font_size_px=round(h * 0.038, 1),
            ),
            TextBlock(
                text=mrp_str,
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.30, 1), "w": round(w * 0.70, 1), "h": round(h * 0.055, 1)},
                confidence=0.95,
                font_size_px=round(h * 0.035, 1),
            ),
            TextBlock(
                text=usp_str,
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.37, 1), "w": round(w * 0.55, 1), "h": round(h * 0.045, 1)},
                confidence=0.93,
                font_size_px=round(h * 0.028, 1),
            ),
            TextBlock(
                text="Mfg Date: 08/2026",
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.43, 1), "w": round(w * 0.40, 1), "h": round(h * 0.045, 1)},
                confidence=0.96,
                font_size_px=round(h * 0.028, 1),
            ),
            TextBlock(
                text=mfg_text,
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.50, 1), "w": round(w * 0.84, 1), "h": round(h * 0.095, 1)},
                confidence=0.94,
                font_size_px=round(h * 0.025, 1),
            ),
            TextBlock(
                text=f"Country of Origin: {p_origin}",
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.62, 1), "w": round(w * 0.45, 1), "h": round(h * 0.045, 1)},
                confidence=0.97,
                font_size_px=round(h * 0.025, 1),
            ),
            TextBlock(
                text=care_text,
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.68, 1), "w": round(w * 0.84, 1), "h": round(h * 0.085, 1)},
                confidence=0.92,
                font_size_px=round(h * 0.022, 1),
            ),
            TextBlock(
                text=f"Batch No: {p_info.get('batch_number') or p_info.get('lot_number') or kwargs.get('batch_number') or 'DF240826A'}",
                bounding_box={"x": round(w * 0.08, 1), "y": round(h * 0.78, 1), "w": round(w * 0.40, 1), "h": round(h * 0.045, 1)},
                confidence=0.96,
                font_size_px=round(h * 0.025, 1),
            ),
        ]

        full_text = "\n".join([b.text for b in blocks])
        return OCRResult(
            full_text=full_text,
            blocks=blocks,
            confidence=0.96,
            language="en",
        )
