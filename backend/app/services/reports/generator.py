import io
from datetime import datetime, timezone
from typing import Any, Dict, List
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import AuditService
from app.core.exceptions import ValidationException
from app.models import ComplianceReport, Declaration, Product, Scan, ScanImage, User
from app.services.reports.docx_generator import DocxReportGenerator
from app.services.reports.pdf_generator import PDFReportGenerator
from app.services.storage import get_storage_service


FIELD_DISPLAY_NAMES = {
    "common_name": "Generic or Common Name",
    "manufacturer_details": "Manufacturer / Packer / Importer Details",
    "country_of_origin": "Country of Origin",
    "net_quantity": "Net Quantity & Unit of Measurement",
    "mfg_date": "Month & Year of Manufacture / Packing",
    "mrp": "Maximum Retail Price (MRP)",
    "unit_sale_price": "Unit Sale Price (USP)",
    "consumer_care": "Consumer Care Grievance Redressal",
}


class ReportCoordinator:
    def __init__(self):
        self.pdf_generator = PDFReportGenerator()
        self.docx_generator = DocxReportGenerator()
        self.storage_service = get_storage_service()

    async def generate_scan_report(
        self,
        db: AsyncSession,
        scan_id: str,
        user_id: str,
        notes: str = None,
    ) -> ComplianceReport:
        # 1. Fetch scan, inspector, declarations, and product
        scan_res = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = scan_res.scalar_one_or_none()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        scan_meta = dict(scan.metadata_json or {})
        img_res = await db.execute(select(ScanImage).where(ScanImage.scan_id == scan_id).order_by(ScanImage.uploaded_at.asc()))
        scan_imgs = img_res.scalars().all()
        latest_by_type = {}
        for img in scan_imgs:
            latest_by_type[img.image_type] = img
        active_imgs = list(latest_by_type.values())
        has_blurry_img = any(not img.analysis_allowed or img.image_quality != "CLEAR" for img in active_imgs)
        if has_blurry_img or scan_meta.get("analysis_blocked_reason") == "IMAGE_TOO_BLURRY":
            raise ValidationException(
                "Cannot generate compliance report: Image quality was insufficient and analysis was blocked. "
                "Please provide a clear packaging image and complete analysis first."
            )

        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()

        product = None
        if scan.product_id:
            prod_res = await db.execute(select(Product).where(Product.id == scan.product_id))
            product = prod_res.scalar_one_or_none()

        decl_res = await db.execute(
            select(Declaration)
            .where(Declaration.scan_id == scan_id)
            .order_by(Declaration.created_at.asc())
        )
        raw_declarations = decl_res.scalars().all()

        # Deduplicate declarations by normalized field_type
        seen_types = set()
        declarations: List[Declaration] = []
        for d in raw_declarations:
            norm_key = d.field_type.lower()
            if norm_key not in seen_types:
                seen_types.add(norm_key)
                declarations.append(d)

        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Fetch audit logs for this scan and related declarations
        from app.models.audit import AuditLog
        audit_res = await db.execute(
            select(AuditLog, User.name, User.role)
            .outerjoin(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.timestamp.desc())
        )
        audit_rows = audit_res.all()
        audit_trail_entries = []
        for log, u_name, u_role in audit_rows:
            meta = log.metadata_json or {}
            if (
                (log.entity_type == "scan" and log.entity_id == scan_id)
                or (meta.get("scan_id") == scan_id)
                or (log.entity_type == "declaration" and meta.get("scan_id") == scan_id)
            ):
                audit_trail_entries.append({
                    "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "user_name": u_name or meta.get("user_name") or "System",
                    "user_role": (u_role or meta.get("user_role") or "System").capitalize(),
                    "action": log.action.replace("_", " "),
                    "notes": meta.get("reviewer_notes") or meta.get("remarks") or meta.get("notes") or "System event logged.",
                })

        # Calculate preliminary AI verdict & check human decisions
        scan_meta = dict(scan.metadata_json or {})
        final_human_decision = scan_meta.get("final_decision")
        finalized_by = scan_meta.get("finalized_by")
        finalized_at = scan_meta.get("finalized_at")
        final_remarks = scan_meta.get("final_remarks") or notes

        confirmed_violations = 0
        uncertain_findings = 0

        formatted_decls = []
        for d in declarations:
            conf = d.confidence_score or 0.0
            if conf >= 0.90:
                conf_level = "HIGH"
            elif conf >= 0.70:
                conf_level = "MEDIUM"
            else:
                conf_level = "LOW"

            is_override = d.reviewer_override
            is_pass = d.is_compliant
            sev = (d.severity or "none").lower()

            if is_pass:
                status_label = "COMPLIANT"
            elif sev == "needs_review" or (conf > 0.0 and conf < 0.70 and not is_override):
                status_label = "NEEDS MANUAL REVIEW"
                uncertain_findings += 1
            else:
                status_label = "NON-COMPLIANT (VIOLATION)"
                if not is_override and conf >= 0.70:
                    confirmed_violations += 1
                elif not is_override:
                    uncertain_findings += 1

            # Format font size
            font_display = None
            if d.font_size_mm:
                font_display = f"Estimated visual size: approximately {d.font_size_mm:.1f} mm — subject to manual verification"

            # Reason & explanation
            reason = d.reviewer_notes or ("Statutory requirement verified." if is_pass else "Non-compliance detected against statutory rules.")
            if not d.is_present:
                reason = f"Mandatory declaration '{FIELD_DISPLAY_NAMES.get(d.field_type, d.field_type)}' is not detected on the package label."

            # Evidence reference
            bbox = d.bounding_box or {}
            if d.extracted_text and bbox.get("w", 0) > 0:
                evidence = f"Label text: \"{d.extracted_text}\" [Region: x={bbox.get('x',0):.0f}, y={bbox.get('y',0):.0f}, w={bbox.get('w',0):.0f}, h={bbox.get('h',0):.0f}]"
            elif d.extracted_text:
                evidence = f"Label text: \"{d.extracted_text}\""
            else:
                evidence = "[Field absent on packaging label]"

            ai_st = (d.original_ai_status or ("compliant" if is_pass else "non_compliant")).upper().replace("_", " ")

            is_officer = bool(d.human_decision and d.human_decision not in ["AUTO-ANALYZED", "NONE"])
            rate = d.violation_detection_rate if d.violation_detection_rate is not None else round(conf * 100.0, 1)
            thresh = d.auto_confirm_threshold if d.auto_confirm_threshold is not None else 80.0
            is_auto = (not is_officer) and (
                d.workflow_decision in ["AUTO_CONFIRMED", "AUTOMATICALLY_CONFIRMED"]
                or getattr(d, "verification_status", None) == "AUTO_CONFIRMED"
                or (d.workflow_decision is None and rate >= thresh and sev != "needs_review")
            )

            verif_method = (
                "System Auto-Confirmation"
                if is_auto
                else (
                    f"Inspector Review ({d.human_decision.title()})"
                    if is_officer
                    else "Manual Inspector Review Required"
                )
            )

            formatted_decls.append({
                "field_type": d.field_type,
                "field_name": FIELD_DISPLAY_NAMES.get(d.field_type, d.field_type.replace("_", " ").title()),
                "extracted_text": d.extracted_text,
                "raw_extracted_value": getattr(d, "raw_extracted_value", None) or d.extracted_text,
                "normalized_numeric_value": getattr(d, "normalized_numeric_value", None),
                "normalized_unit": getattr(d, "normalized_unit", None),
                "has_conflict": getattr(d, "has_conflict", False),
                "confidence_score": round(conf, 2),
                "confidence_level": conf_level,
                "font_size_mm": d.font_size_mm,
                "font_size_display": font_display,
                "is_compliant": is_pass,
                "is_present": d.is_present,
                "status_label": status_label,
                "original_ai_status": ai_st,
                "violation_detection_rate": rate,
                "auto_confirm_threshold": thresh,
                "workflow_decision": "AUTO_CONFIRMED" if is_auto else ("FINALIZED" if is_officer else "MANUAL_REVIEW_REQUIRED"),
                "decision_method": "SYSTEM_THRESHOLD" if is_auto else "MANUAL",
                "verification_status": "AUTO_CONFIRMED" if is_auto else (f"INSPECTOR_{d.human_decision.upper()}" if is_officer else "MANUAL_REVIEW_REQUIRED"),
                "verification_source": "SYSTEM_THRESHOLD" if is_auto else ("INSPECTOR" if is_officer else "MANUAL"),
                "verification_method": verif_method,
                "inspector_override": d.human_decision.title() if is_officer else "None",
                "final_finding": "Compliant" if is_pass else "Non-Compliant",
                "decision_reason": d.decision_reason,
                "human_decision": (d.human_decision or ("OVERRIDDEN" if is_override else "AUTO-ANALYZED")).upper(),
                "reviewed_by": d.reviewed_by,
                "reviewed_at": d.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if d.reviewed_at else None,
                "rule_reference": d.rule_reference or "Legal Metrology (Packaged Commodities) Rules, 2011",
                "severity": d.severity or "none",
                "reviewer_override": d.reviewer_override,
                "reviewer_notes": d.reviewer_notes,
                "reason": reason,
                "evidence": evidence,
            })

        # Calculate preliminary vs final overall status
        if confirmed_violations > 0:
            ai_preliminary_status = "non_compliant"
            ai_preliminary_label = "NON-COMPLIANT (VIOLATION)"
        elif uncertain_findings > 0:
            ai_preliminary_status = "needs_review"
            ai_preliminary_label = "NEEDS MANUAL REVIEW"
        else:
            ai_preliminary_status = "compliant"
            ai_preliminary_label = "VERIFIED COMPLIANT"

        if final_human_decision:
            overall_status = final_human_decision.lower()
            if overall_status == "compliant":
                overall_label = "VERIFIED COMPLIANT (HUMAN FINALIZED)"
                statutory_assessment = "Statutory compliance verified and finalized by the authorized Legal Metrology officer after verification."
            elif overall_status == "needs_review":
                overall_label = "NEEDS MANUAL REVIEW"
                statutory_assessment = "Inspection findings require manual review and verification by the authorized Legal Metrology officer before any statutory determination."
            else:
                overall_label = "NON-COMPLIANT (HUMAN FINALIZED)"
                statutory_assessment = "Potential non-compliance identified. Final enforcement action is subject to verification and decision by the competent Legal Metrology authority."
        else:
            overall_status = ai_preliminary_status
            overall_label = ai_preliminary_label
            if overall_status == "non_compliant":
                statutory_assessment = "Potential non-compliance identified. Final enforcement action is subject to verification and decision by the competent Legal Metrology authority."
            elif overall_status == "needs_review":
                statutory_assessment = "Inspection findings require manual review and verification by the authorized Legal Metrology officer before any statutory determination."
            else:
                statutory_assessment = "All mandatory declarations specified under the Legal Metrology (Packaged Commodities) Rules, 2011 are duly present, legibly displayed, and meet statutory requirements based on automated verification."

        # Calculate batch investigation information
        from sqlalchemy import func
        from sqlalchemy.orm import selectinload

        related_batch_inspections = 0
        batch_inspections_requiring_attention = 0
        if scan.batch_number and scan.batch_number.strip():
            b_scans_stmt = (
                select(Scan)
                .where(func.lower(Scan.batch_number) == scan.batch_number.strip().lower())
                .options(selectinload(Scan.declarations))
            )
            b_scans = (await db.execute(b_scans_stmt)).scalars().all()
            related_batch_inspections = len(b_scans)
            for bs in b_scans:
                meta_bs = bs.metadata_json or {}
                if meta_bs.get("final_decision") == "non_compliant" or any(not d.is_compliant for d in bs.declarations):
                    batch_inspections_requiring_attention += 1

        batch_legal_note = (
            "Batch-level information is provided to support inspection and investigation. "
            "Presence of an issue in one inspected package does not by itself establish that all products in the batch "
            "are non-compliant. Further verification is subject to the competent authority's procedures."
        )

        first_decl = declarations[0] if declarations else None
        violation_detection_rate = (
            first_decl.violation_detection_rate
            if first_decl and first_decl.violation_detection_rate is not None
            else scan_meta.get("violation_detection_rate", 0.0)
        )
        auto_confirm_threshold = (
            first_decl.auto_confirm_threshold
            if first_decl and first_decl.auto_confirm_threshold is not None
            else scan_meta.get("auto_confirm_threshold", 80.0)
        )
        thresh_calc = auto_confirm_threshold or 80.0
        auto_confirmed_count = sum(
            1 for d in declarations
            if (not (d.human_decision and d.human_decision not in ["AUTO-ANALYZED", "NONE"]))
            and (
                d.workflow_decision in ["AUTO_CONFIRMED", "AUTOMATICALLY_CONFIRMED"]
                or getattr(d, "verification_status", None) == "AUTO_CONFIRMED"
                or (
                    d.workflow_decision is None
                    and ((d.violation_detection_rate if d.violation_detection_rate is not None else ((d.confidence_score or 0.0) * 100.0)) >= (d.auto_confirm_threshold or thresh_calc))
                    and getattr(d, "severity", None) != "needs_review"
                )
            )
        )
        inspector_resolved_count = sum(
            1 for d in declarations
            if (d.human_decision and d.human_decision not in ["AUTO-ANALYZED", "NONE"])
        )
        manual_review_count = sum(
            1 for d in declarations
            if (not (d.human_decision and d.human_decision not in ["AUTO-ANALYZED", "NONE"]))
            and not (
                d.workflow_decision in ["AUTO_CONFIRMED", "AUTOMATICALLY_CONFIRMED"]
                or getattr(d, "verification_status", None) == "AUTO_CONFIRMED"
                or (
                    d.workflow_decision is None
                    and ((d.violation_detection_rate if d.violation_detection_rate is not None else ((d.confidence_score or 0.0) * 100.0)) >= (d.auto_confirm_threshold or thresh_calc))
                    and getattr(d, "severity", None) != "needs_review"
                )
            )
        )
        total_decls_count = len(declarations)
        has_auto = auto_confirmed_count > 0
        has_manual = manual_review_count > 0
        workflow_decision = "AUTO_CONFIRMED" if (has_auto and not has_manual) else ("MANUAL_REVIEW_REQUIRED" if has_manual else "FINALIZED")
        decision_method = "SYSTEM_THRESHOLD" if (has_auto and not has_manual) else "MANUAL"

        # Derive authoritative overall status from resolved findings
        has_any_violation = any(not d.is_compliant for d in declarations)
        if has_any_violation:
            overall_status = "non_compliant"
            overall_label = "NON-COMPLIANT (STATUTORY VIOLATION)"
            statutory_assessment = "Potential non-compliance identified based on verified declaration findings. Final enforcement action is subject to verification and decision by the competent Legal Metrology authority."
        elif manual_review_count > 0:
            overall_status = "needs_review"
            overall_label = "NEEDS MANUAL REVIEW"
            statutory_assessment = "Inspection findings require manual review and verification by the authorized Legal Metrology officer before any statutory determination."
        else:
            overall_status = "compliant"
            overall_label = "VERIFIED COMPLIANT"
            statutory_assessment = "All mandatory declarations specified under the Legal Metrology (Packaged Commodities) Rules, 2011 are duly present, legibly displayed, and meet statutory requirements based on automated verification and inspector review."

        decision_basis = f"{total_decls_count}/{total_decls_count} declarations resolved ({auto_confirmed_count} Auto-Confirmed, {inspector_resolved_count} Inspector Reviewed, {manual_review_count} Unresolved)"

        # Build template context
        context: Dict[str, Any] = {
            "report_id": report_id,
            "scan_id": scan.id,
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "inspector_name": user.name if user else "Enforcement Officer",
            "inspector_role": (user.role if user else "Inspector").capitalize(),
            "product_name": product.name if product else "Scanned Packaged Commodity",
            "product_brand": product.brand if product else "N/A",
            "product_category": product.category if product else "Packaged Goods",
            "manufacturer_name": product.manufacturer_name if product else "Declared on label",
            "manufacturer_address": product.manufacturer_address if product else "Refer label inspection",
            "location_name": scan.location_name or "Retail Store / Inspection Point",
            "country_of_origin": product.country_of_origin if product else "India",
            "batch_number": scan.batch_number,
            "batch_number_source": scan.batch_number_source or "manual",
            "batch_status": scan.batch_status or "normal",
            "related_batch_inspections": related_batch_inspections,
            "batch_inspections_requiring_attention": batch_inspections_requiring_attention,
            "batch_legal_note": batch_legal_note,
            "ai_preliminary_status": ai_preliminary_status,
            "ai_preliminary_label": ai_preliminary_label,
            "final_human_decision": final_human_decision,
            "finalized_by": finalized_by or (user.name if user else None),
            "finalized_at": finalized_at or now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "final_remarks": final_remarks or notes,
            "overall_status": overall_status,
            "overall_label": overall_label,
            "decision_basis": decision_basis,
            "auto_confirmed_count": auto_confirmed_count,
            "inspector_resolved_count": inspector_resolved_count,
            "manual_review_count": manual_review_count,
            "unresolved_count": manual_review_count,
            "total_declarations_count": total_decls_count,
            "violation_detection_rate": violation_detection_rate,
            "auto_confirm_threshold": auto_confirm_threshold,
            "workflow_decision": workflow_decision,
            "decision_method": decision_method,
            "workflow_disclaimer": "Automated confirmation is a workflow routing mechanism based on the configured automatic-confirmation threshold. Final statutory compliance determinations, violation citations, and legal enforcement actions remain exclusively under the jurisdiction of authorized Legal Metrology officers.",
            "statutory_assessment": statutory_assessment,
            "declarations": formatted_decls,
            "audit_trail": audit_trail_entries[:15],
            "custom_notes": notes,
        }


        # 2. Generate PDF and DOCX bytes
        pdf_bytes = self.pdf_generator.generate_pdf_bytes(context)
        docx_bytes = self.docx_generator.generate_docx_bytes(context)

        # 3. Upload both to storage
        pdf_url, pdf_key = await self.storage_service.upload_file(
            file_obj=io.BytesIO(pdf_bytes),
            filename=f"compliance_report_{scan_id}.pdf",
            content_type="application/pdf",
            folder="reports",
        )

        docx_url, docx_key = await self.storage_service.upload_file(
            file_obj=io.BytesIO(docx_bytes),
            filename=f"compliance_report_{scan_id}.docx",
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            folder="reports",
        )

        # 4. Save ComplianceReport record
        report = ComplianceReport(
            id=report_id,
            scan_id=scan.id,
            generated_by=user_id,
            overall_status=overall_status,
            pdf_url=pdf_url,
            docx_url=docx_url,
            summary_data=context,
            generated_at=now,
        )
        db.add(report)

        # 5. Log audit entry
        await AuditService.log_action(
            db=db,
            action="REPORT_GENERATED",
            entity_type="compliance_report",
            entity_id=report_id,
            user_id=user_id,
            metadata={"scan_id": scan.id, "overall_status": overall_status},
        )

        await db.commit()
        await db.refresh(report)
        return report
