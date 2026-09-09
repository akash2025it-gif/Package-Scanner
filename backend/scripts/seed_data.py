import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from app.models import AuditLog, ComplianceReport, Declaration, Product, Scan, ScanImage, User


async def seed_database():
    print("[*] Initializing database schema...")
    await init_db()

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        existing_users = (await db.execute(select(User))).scalars().first()
        if existing_users:
            print("[INFO] Database already contains data. Skipping seeding.")
            return

        print("[*] Creating default users with RBAC roles...")
        now = datetime.now(timezone.utc)

        admin = User(
            id=str(uuid.uuid4()),
            name="Rajesh Kumar Verma",
            email="admin@packcheck.gov.in",
            phone="+919876543210",
            password_hash=hash_password("admin123"),
            role="admin",
            department="Central Legal Metrology Division",
            region="National HQ",
            is_active=True,
            created_at=now - timedelta(days=60),
        )

        inspector_delhi = User(
            id=str(uuid.uuid4()),
            name="Inspector Vikram Sharma",
            email="inspector.sharma@packcheck.gov.in",
            phone="+919876543212",
            password_hash=hash_password("inspector123"),
            role="inspector",
            department="Field Inspection Squad - Delhi North",
            region="Delhi NCR",
            is_active=True,
            created_at=now - timedelta(days=30),
        )

        inspector_ka = User(
            id=str(uuid.uuid4()),
            name="Inspector Suresh Reddy",
            email="inspector.reddy@packcheck.gov.in",
            phone="+919876543213",
            password_hash=hash_password("inspector123"),
            role="inspector",
            department="Legal Metrology Cell - Bengaluru Urban",
            region="Karnataka",
            is_active=True,
            created_at=now - timedelta(days=20),
        )

        inspector_mh = User(
            id=str(uuid.uuid4()),
            name="Inspector Sunita Rao",
            email="inspector.rao@packcheck.gov.in",
            phone="+919876543211",
            password_hash=hash_password("inspector123"),
            role="inspector",
            department="Enforcement Directorate - Mumbai",
            region="Maharashtra",
            is_active=True,
            created_at=now - timedelta(days=45),
        )

        db.add_all([admin, inspector_delhi, inspector_ka, inspector_mh])
        await db.flush()

        print("Creating packaged product catalog...")
        p1 = Product(
            id=str(uuid.uuid4()),
            name="Aashirvaad Superior MP Whole Wheat Atta",
            brand="Aashirvaad",
            category="Food Grains & Flours",
            manufacturer_name="ITC Limited",
            manufacturer_address="37, J.L. Nehru Road, Kolkata - 700071, West Bengal",
            country_of_origin="India",
            barcode="8901030383748",
            created_at=now - timedelta(days=15),
        )

        p2 = Product(
            id=str(uuid.uuid4()),
            name="Dove Intense Repair Shampoo",
            brand="Dove",
            category="Personal Care & Cosmetics",
            manufacturer_name="Hindustan Unilever Limited",
            manufacturer_address="Unilever House, B.D. Sawant Marg, Chakala, Andheri (E), Mumbai - 400099",
            country_of_origin="India",
            barcode="8901030826450",
            created_at=now - timedelta(days=14),
        )

        p3 = Product(
            id=str(uuid.uuid4()),
            name="Borges Extra Virgin Olive Oil 1L",
            brand="Borges",
            category="Edible Oils",
            manufacturer_name="Aceites Borges Pont S.A.U., Spain / Imp: Borges India Pvt Ltd",
            manufacturer_address="Unit No. 2, Ground Floor, Bestech Business Tower, Sector 48, Gurugram - 122018",
            country_of_origin="Spain",
            barcode="8410179010049",
            created_at=now - timedelta(days=10),
        )

        p4 = Product(
            id=str(uuid.uuid4()),
            name="Parle-G Gold Glucose Biscuits",
            brand="Parle",
            category="Packaged Snacks & Bakery",
            manufacturer_name="Parle Products Pvt. Ltd.",
            manufacturer_address="North Level Crossing, Vile Parle East, Mumbai - 400057",
            country_of_origin="India",
            barcode="8901719101015",
            created_at=now - timedelta(days=8),
        )

        db.add_all([p1, p2, p3, p4])
        await db.flush()

        print("Creating realistic scans and declaration evaluations...")
        # 1. Compliant Scan (Atta 5kg)
        scan1 = Scan(
            id=str(uuid.uuid4()),
            product_id=p1.id,
            inspector_id=inspector_delhi.id,
            source="physical_store",
            status="closed",
            location_name="Big Bazaar, Connaught Place, New Delhi",
            gps_coordinates="28.6315, 77.2167",
            created_at=now - timedelta(days=5),
        )
        db.add(scan1)
        await db.flush()

        img1 = ScanImage(
            id=str(uuid.uuid4()),
            scan_id=scan1.id,
            image_url="/api/v1/storage/scans/sample_atta_label.jpg",
            storage_key="scans/sample_atta_label.jpg",
            image_type="front",
            width_px=1200,
            height_px=1600,
            uploaded_at=now - timedelta(days=5),
        )
        db.add(img1)

        decls_scan1 = [
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="common_name",
                extracted_text="Whole Wheat Flour (Atta)",
                bounding_box={"x": 120.0, "y": 140.0, "w": 400.0, "h": 50.0},
                confidence_score=0.98,
                font_size_mm=6.5,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(a) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=98.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (98%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="net_quantity",
                extracted_text="Net Quantity: 5 kg",
                bounding_box={"x": 120.0, "y": 220.0, "w": 280.0, "h": 60.0},
                confidence_score=0.97,
                font_size_mm=8.2,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(d) read with Rule 8 & Second Schedule",
                severity="none",
                violation_detection_rate=97.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (97%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="mrp",
                extracted_text="MRP ₹ 245.00 (inclusive of all taxes)",
                bounding_box={"x": 120.0, "y": 300.0, "w": 450.0, "h": 45.0},
                confidence_score=0.96,
                font_size_mm=6.0,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(f) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=96.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (96%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="mfg_date",
                extracted_text="Mfg Date: 08/2026",
                bounding_box={"x": 120.0, "y": 360.0, "w": 220.0, "h": 35.0},
                confidence_score=0.95,
                font_size_mm=4.0,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(e) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=95.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (95%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="manufacturer_details",
                extracted_text="Manufactured & Packed by: ITC Limited, 37 J.L. Nehru Road, Kolkata - 700071",
                bounding_box={"x": 120.0, "y": 420.0, "w": 520.0, "h": 65.0},
                confidence_score=0.94,
                font_size_mm=3.5,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(b) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=94.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (94%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan1.id,
                field_type="consumer_care",
                extracted_text="Consumer Care: ITC Care Cell, Toll Free: 1800-425-4444, Email: itccares@itc.in",
                bounding_box={"x": 120.0, "y": 500.0, "w": 540.0, "h": 50.0},
                confidence_score=0.93,
                font_size_mm=3.0,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(h) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=93.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (93%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
        ]
        db.add_all(decls_scan1)

        # 2. Non-Compliant Scan (Dove Shampoo - Missing tax statement & Font size deficit)
        scan2 = Scan(
            id=str(uuid.uuid4()),
            product_id=p2.id,
            inspector_id=inspector_ka.id,
            source="physical_store",
            status="needs_review",
            location_name="Reliance Retail, Indiranagar, Bengaluru",
            gps_coordinates="12.9784, 77.6408",
            created_at=now - timedelta(days=2),
        )
        db.add(scan2)
        await db.flush()

        img2 = ScanImage(
            id=str(uuid.uuid4()),
            scan_id=scan2.id,
            image_url="/api/v1/storage/scans/sample_shampoo_label.jpg",
            storage_key="scans/sample_shampoo_label.jpg",
            image_type="back",
            width_px=1080,
            height_px=1920,
            uploaded_at=now - timedelta(days=2),
        )
        db.add(img2)

        decls_scan2 = [
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan2.id,
                field_type="mrp",
                extracted_text="MRP Rs. 420.00",
                bounding_box={"x": 80.0, "y": 280.0, "w": 320.0, "h": 40.0},
                confidence_score=0.92,
                font_size_mm=2.5,
                is_present=True,
                is_compliant=False,
                rule_reference="Rule 6(1)(f) of LMPC Rules, 2011",
                severity="critical",
                reviewer_notes="Violates Rule 6(1)(f): Missing statutory mandatory phrase '(inclusive of all taxes)'.",
                violation_detection_rate=92.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (92%) meets the configured automatic-confirmation threshold (80%). The non-compliance finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan2.id,
                field_type="net_quantity",
                extracted_text="Net Vol: 650 ml",
                bounding_box={"x": 80.0, "y": 210.0, "w": 250.0, "h": 30.0},
                confidence_score=0.94,
                font_size_mm=2.1,  # Deficit for >500ml slab (minimum 4.0mm required)
                is_present=True,
                is_compliant=False,
                rule_reference="Second Schedule of LMPC Rules, 2011",
                severity="major",
                reviewer_notes="Font size (2.1mm) is below the minimum mandatory height of 4.0mm for net volume 650ml.",
                violation_detection_rate=94.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (94%) meets the configured automatic-confirmation threshold (80%). The non-compliance finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan2.id,
                field_type="common_name",
                extracted_text="Hair Cleanser (Shampoo)",
                bounding_box={"x": 80.0, "y": 120.0, "w": 350.0, "h": 45.0},
                confidence_score=0.96,
                font_size_mm=4.0,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(a) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=96.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (96%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
            Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan2.id,
                field_type="mfg_date",
                extracted_text="Mfg: 05/2026",
                bounding_box={"x": 80.0, "y": 350.0, "w": 200.0, "h": 30.0},
                confidence_score=0.95,
                font_size_mm=3.0,
                is_present=True,
                is_compliant=True,
                rule_reference="Rule 6(1)(e) of LMPC Rules, 2011",
                severity="none",
                violation_detection_rate=95.0,
                auto_confirm_threshold=80.0,
                workflow_decision="AUTO_CONFIRMED",
                decision_method="SYSTEM_THRESHOLD",
                verification_status="AUTO_CONFIRMED",
                verification_source="SYSTEM_THRESHOLD",
                decision_reason="Declaration confidence (95%) meets the configured automatic-confirmation threshold (80%). The finding was automatically confirmed for the inspection workflow.",
            ),
        ]
        db.add_all(decls_scan2)

        # 3. E-commerce Scan (Imported Olive Oil - Missing Country of Origin on product card)
        scan3 = Scan(
            id=str(uuid.uuid4()),
            product_id=p3.id,
            inspector_id=inspector_mh.id,
            source="ecommerce",
            source_url="https://www.quickcomm-demo.in/p/borges-olive-oil-1l",
            status="reviewed",
            location_name="Mumbai E-Commerce Surveillance Cell",
            created_at=now - timedelta(days=1),
        )
        db.add(scan3)
        await db.flush()

        # Generate sample Compliance Report for Scan 1
        rep1 = ComplianceReport(
            id=str(uuid.uuid4()),
            scan_id=scan1.id,
            generated_by=inspector_delhi.id,
            overall_status="compliant",
            pdf_url=f"/api/v1/reports/{scan1.id}/pdf",
            docx_url=f"/api/v1/reports/{scan1.id}/docx",
            summary_data={
                "scan_id": scan1.id,
                "inspector_name": inspector_delhi.name,
                "product_name": p1.name,
                "overall_status": "compliant",
            },
            generated_at=now - timedelta(days=4),
        )
        db.add(rep1)

        # Audit log entries
        audit1 = AuditLog(
            id=str(uuid.uuid4()),
            user_id=admin.id,
            action="SYSTEM_SEEDED",
            entity_type="system",
            entity_id="packcheck_init",
            timestamp=now - timedelta(days=60),
            metadata_json={"details": "Initial seed data loaded successfully"},
        )
        db.add(audit1)

        await db.commit()
        print("[SUCCESS] Database seeding complete! Sample users, products, scans, declarations, and reports generated.")


if __name__ == "__main__":
    asyncio.run(seed_database())
