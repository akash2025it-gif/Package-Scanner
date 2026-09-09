import re
from typing import Dict, List, Optional
from app.ai.detectors.base import DetectedRegion, RegionDetector
from app.ai.ocr.base import OCRResult, TextBlock


class HeuristicRegionDetector(RegionDetector):
    """
    Intelligent Layout & Keyword-driven Region Detector.
    Matches extracted OCR blocks with packaging declaration patterns to localize regions.
    """

    PATTERNS = {
        "manufacturer_details": re.compile(r"(?:mfg\s+by|manufactured\s+(?:\&?\s*packed\s+)?by|packed\s+by|marketed\s+by|imported\s+by|mfg\s*\&?\s*pkd|regd\.\s*office|fssai|lic\.?\s*no)", re.IGNORECASE),
        "consumer_care": re.compile(r"(?:consumer\s+care|customer\s+care|feedback|complaints|toll\s*free|care@|helpline)", re.IGNORECASE),
        "country_of_origin": re.compile(r"(?:country\s+of\s+origin|made\s+in|product\s+of|origin\s*:)", re.IGNORECASE),
        "unit_sale_price": re.compile(r"(?:unit\s+sale\s+price|u\.?s\.?p\.?|(?:₹|\brs\.?\b|\binr\b)\s*[0-9]+(?:\.[0-9]+)?\s*\/\s*(?:g|kg|ml|l|unit|N|count|piece|gm))", re.IGNORECASE),
        "mrp": re.compile(r"(?:m\.?r\.?p\.?|max(?:imum)?\s+retail\s+price|(?:₹|\brs\.?\b|\binr\b)\s*[0-9]+(?:\.[0-9]+)?)", re.IGNORECASE),
        "mfg_date": re.compile(r"(?:mfg|pkd|packed|pkg|manufactured|date|mfd)[\s\:\.\/]+(?:[0-9]{1,2}[\/\-\.][0-9]{2,4}|[a-zA-Z]{3,9}\s+[0-9]{4})", re.IGNORECASE),
        "net_quantity": re.compile(r"(?:net\s+(?:wt\.?|weight|qty\.?|quantity|content|volume)|\b[0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|gms|ml|l|ltr|oz|mg|count|pcs|units|n|u)\b)", re.IGNORECASE),
        "batch_number": re.compile(r"\b(?:batch(?:\s*(?:no\.?|num(?:ber)?|code))?|lot(?:\s*(?:no\.?|num(?:ber)?|code))?|b\.?\s*no\.?|l\.?\s*no\.?)\s*[:\-\.]?\s*([A-Za-z0-9\-\/]+)", re.IGNORECASE),
        "common_name": re.compile(r"\b(?:atta|flour|wheat\s+flour|biscuit|biscuits|cookies|rusk|oil|edible\s+oil|mustard\s+oil|refined\s+oil|soap|toilet\s+soap|detergent|shampoo|juice|snack|chips|potato\s+chips|namkeen|tea|coffee|rice|basmati|dal|pulses|sugar|salt|spices|pure|refined|whole\s+wheat|dry\s*fruits|almonds|cashew|walnuts|pistachios|raisins|noodles|pasta|cereal|oats|milk|dairy|ghee|butter|paneer|cheese)\b", re.IGNORECASE),
    }

    LABEL_PATTERNS = {
        "net_quantity": re.compile(r"^net\s+(?:wt\.?|weight|qty\.?|quantity|content|volume)[\s\:\.\-]*$", re.IGNORECASE),
        "mrp": re.compile(r"^(?:m\.?r\.?p\.?|max(?:imum)?\s+retail\s+price)[\s\:\.\-]*$", re.IGNORECASE),
        "batch_number": re.compile(r"^(?:batch(?:\s*(?:no\.?|num(?:ber)?|code))?|lot(?:\s*(?:no\.?|num(?:ber)?|code))?|b\.?\s*no\.?|l\.?\s*no\.?)[\s\:\.\-]*$", re.IGNORECASE),
        "unit_sale_price": re.compile(r"^(?:unit\s+sale\s+price|u\.?s\.?p\.?)[\s\:\.\-]*$", re.IGNORECASE),
        "mfg_date": re.compile(r"^(?:mfg|pkd|packed|pkg|manufactured|date\s+of\s+mfg)[\s\:\.\-]*$", re.IGNORECASE),
    }

    VALUE_PATTERNS = {
        "net_quantity": re.compile(r"\b[0-9]+(?:\.[0-9]+)?\s*(?:kg|g|gm|gms|ml|l|ltr|oz|mg|count|pcs|units|n|u)\b", re.IGNORECASE),
        "mrp": re.compile(r"(?:₹|\brs\.?\b|\binr\b)?\s*[0-9]+(?:\.[0-9]{2})?", re.IGNORECASE),
        "batch_number": re.compile(r"^[A-Za-z0-9\-\/]{3,}$"),
        "unit_sale_price": re.compile(r"(?:₹|\brs\.?\b|\binr\b)?\s*[0-9]+(?:\.[0-9]+)?\s*\/\s*(?:g|kg|ml|l|unit|N|count|piece|gm)", re.IGNORECASE),
    }

    async def detect_regions(self, image_bytes: bytes, ocr_result: Optional[OCRResult] = None) -> List[DetectedRegion]:
        if not ocr_result or not ocr_result.blocks:
            return []

        regions: List[DetectedRegion] = []
        used_blocks = set()

        for field_type, pattern in self.PATTERNS.items():
            matching_blocks = []
            for idx, block in enumerate(ocr_result.blocks):
                if idx not in used_blocks and pattern.search(block.text):
                    matching_blocks.append((idx, block))

            # Proximity check: If field is net_quantity or mrp and matched block is only a label header,
            # find an adjacent value block to the right on the same horizontal band
            label_pat = self.LABEL_PATTERNS.get(field_type)
            val_pat = self.VALUE_PATTERNS.get(field_type)

            if label_pat and val_pat and matching_blocks:
                has_value = any(val_pat.search(b.text) for _, b in matching_blocks)
                if not has_value:
                    # Look for nearest unassigned block to the right or immediately below with matching value
                    for _, lbl_block in matching_blocks:
                        lbl_x = lbl_block.bounding_box.get("x", 0.0)
                        lbl_y = lbl_block.bounding_box.get("y", 0.0)
                        lbl_w = lbl_block.bounding_box.get("w", 0.0)
                        lbl_h = lbl_block.bounding_box.get("h", 0.0)

                        best_candidate = None
                        best_dist = float("inf")

                        for c_idx, candidate in enumerate(ocr_result.blocks):
                            if c_idx in used_blocks or any(c_idx == m[0] for m in matching_blocks):
                                continue
                            if not val_pat.search(candidate.text):
                                continue

                            c_x = candidate.bounding_box.get("x", 0.0)
                            c_y = candidate.bounding_box.get("y", 0.0)
                            c_h = candidate.bounding_box.get("h", 0.0)

                            # Check horizontal alignment (roughly same line)
                            v_diff = abs(c_y - lbl_y)
                            h_dist = c_x - (lbl_x + lbl_w)

                            # Same line (or within 1.5x height) and to the right within reasonable gap
                            if v_diff <= max(lbl_h, c_h, 30.0) * 1.8 and -10.0 <= h_dist <= 300.0:
                                if h_dist < best_dist:
                                    best_dist = h_dist
                                    best_candidate = (c_idx, candidate)

                        if best_candidate:
                            matching_blocks.append(best_candidate)
                            break

            if matching_blocks:
                # Merge bounding box of all matching blocks for this field
                min_x = min(b.bounding_box.get("x", 0.0) for _, b in matching_blocks)
                min_y = min(b.bounding_box.get("y", 0.0) for _, b in matching_blocks)
                max_x = max(b.bounding_box.get("x", 0.0) + b.bounding_box.get("w", 0.0) for _, b in matching_blocks)
                max_y = max(b.bounding_box.get("y", 0.0) + b.bounding_box.get("h", 0.0) for _, b in matching_blocks)

                # Order text left-to-right, top-to-bottom
                sorted_blocks = sorted(matching_blocks, key=lambda pair: (pair[1].bounding_box.get("y", 0.0), pair[1].bounding_box.get("x", 0.0)))
                combined_text = " ".join([b.text for _, b in sorted_blocks])
                avg_conf = sum([b.confidence for _, b in matching_blocks]) / len(matching_blocks)
                avg_font = max([b.font_size_px or 20.0 for _, b in matching_blocks])

                for idx, _ in matching_blocks:
                    used_blocks.add(idx)

                regions.append(
                    DetectedRegion(
                        field_type=field_type,
                        bounding_box={
                            "x": float(min_x),
                            "y": float(min_y),
                            "w": float(max_x - min_x),
                            "h": float(max_y - min_y),
                        },
                        confidence=round(avg_conf, 2),
                        text=combined_text,
                        font_size_px=float(avg_font),
                    )
                )

        return regions
