import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import Settings
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.rules.config_loader import RuleConfigLoader
from app.rules.engine import RuleEngine
from app.services.reports.pdf_generator import PDFReportGenerator
from app.services.reports.docx_generator import DocxReportGenerator


def test_security_settings_validation():
    """Verify strict production security validations on SECRET_KEY, DATABASE_URL and passwords."""
    # Ensure clean production environment state
    for k in ["APP_ENV", "VERCEL", "SECRET_KEY", "DATABASE_URL", "INITIAL_ADMIN_PASSWORD", "INITIAL_INSPECTOR_PASSWORD"]:
        os.environ.pop(k, None)

    os.environ["APP_ENV"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://prod_user:prod_pass@db.packcheck.gov.in:5432/packcheck_prod"

    # Test 1: Missing SECRET_KEY in production raises error
    os.environ["SECRET_KEY"] = ""
    with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR: SECRET_KEY"):
        Settings()

    # Test 2: Insecure default key in production raises error
    os.environ["SECRET_KEY"] = "packcheck-super-secret-production-key-change-me"
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION"):
        Settings()

    # Test 3: Short key (< 32 chars) in production raises error
    os.environ["SECRET_KEY"] = "short-key-123"
    with pytest.raises(ValueError, match="CRITICAL SECURITY CONFIGURATION"):
        Settings()

    # Test 4: Production rejects missing DATABASE_URL
    strong_key = "a-very-strong-production-signing-secret-key-that-is-at-least-32-chars-long"
    os.environ["SECRET_KEY"] = strong_key
    os.environ["DATABASE_URL"] = ""
    with pytest.raises(ValueError, match="CRITICAL CONFIGURATION ERROR: DATABASE_URL"):
        Settings()

    # Test 5: Production strictly rejects ephemeral SQLite
    os.environ["DATABASE_URL"] = "sqlite:///tmp/packcheck.db"
    with pytest.raises(ValueError, match="Ephemeral SQLite is strictly prohibited in production"):
        Settings()

    # Test 6: Valid production configuration with strong SECRET_KEY & PostgreSQL
    os.environ["DATABASE_URL"] = "postgresql://prod_user:prod_pass@db.packcheck.gov.in:5432/packcheck_prod"
    s = Settings()
    assert s.SECRET_KEY == strong_key
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
    # In production, initial passwords must be None when unset (NO predictable fallback passwords)
    assert s.INITIAL_ADMIN_PASSWORD is None
    assert s.INITIAL_INSPECTOR_PASSWORD is None

    # Test 7: Production accepts explicitly supplied initial admin & inspector credentials
    os.environ["INITIAL_ADMIN_PASSWORD"] = "StrongAdmin#Pass2026!"
    os.environ["INITIAL_INSPECTOR_PASSWORD"] = "StrongInspector#Pass2026!"
    s_creds = Settings()
    assert s_creds.INITIAL_ADMIN_PASSWORD == "StrongAdmin#Pass2026!"
    assert s_creds.INITIAL_INSPECTOR_PASSWORD == "StrongInspector#Pass2026!"

    # Clean up environment
    for k in ["APP_ENV", "VERCEL", "SECRET_KEY", "DATABASE_URL", "INITIAL_ADMIN_PASSWORD", "INITIAL_INSPECTOR_PASSWORD"]:
        os.environ.pop(k, None)


def test_database_url_normalization():
    """Verify PostgreSQL and SQLite driver dialect normalization across environments."""
    # Postgres dialects normalized to asyncpg
    url1 = Settings.validate_database_url("postgres://user:pass@host:5432/dbname")
    assert url1.startswith("postgresql+asyncpg://")

    url2 = Settings.validate_database_url("postgresql://user:pass@host:5432/dbname")
    assert url2.startswith("postgresql+asyncpg://")

    url3 = Settings.validate_database_url("postgresql+asyncpg://user:pass@host:5432/dbname")
    assert url3.startswith("postgresql+asyncpg://")

    # In development, SQLite is permitted and normalized to aiosqlite
    os.environ["APP_ENV"] = "development"
    os.environ.pop("VERCEL", None)
    url4 = Settings.validate_database_url("sqlite:///tmp/test.db")
    assert url4.startswith("sqlite+aiosqlite://")
    os.environ.pop("APP_ENV", None)


def test_jwt_auth_and_rbac():
    """Verify password hashing, JWT generation, and role decoding."""
    # Password hashing
    raw_pass = "ComplexGovPassword#2026"
    hashed = hash_password(raw_pass)
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

    # JWT generation & decoding
    token = create_access_token(subject="user-123", role="inspector")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "inspector"
    assert payload["type"] == "access"


def test_lmpc_statutory_rules():
    """Verify accuracy of LMPC 2011 Rule 6(1) validations."""
    loader = RuleConfigLoader.get_instance()
    engine = RuleEngine()

    # Rule 6(1)(b) Manufacturer Details
    mfg_rule = loader.get_rules_for_field("manufacturer_details")[0]
    
    # Heading alone MUST fail
    res_heading = engine.evaluate_field(mfg_rule, "Manufactured & Packed by:")
    assert res_heading.is_compliant is False
    assert res_heading.severity == "critical"

    # Full entity name MUST pass
    res_full_mfg = engine.evaluate_field(mfg_rule, "Manufactured & Packed by: Himalayan Naturals Pvt. Ltd., Solan, H.P. - 173212")
    assert res_full_mfg.is_compliant is True

    # Rule 6(1)(f) MRP
    mrp_rule = loader.get_rules_for_field("mrp")[0]
    
    # Missing tax statement MUST fail
    res_mrp_notax = engine.evaluate_field(mrp_rule, "Maximum Retail Price (MRP): Rs 220.00", metadata={})
    assert res_mrp_notax.is_compliant is False
    assert res_mrp_notax.severity == "critical"

    # With tax statement MUST pass
    res_mrp_tax = engine.evaluate_field(mrp_rule, "Maximum Retail Price (MRP): Rs 220.00 (Inclusive of all taxes)", metadata={})
    assert res_mrp_tax.is_compliant is True

    # With tax statement in full OCR text metadata MUST pass
    res_mrp_multi = engine.evaluate_field(
        mrp_rule, 
        "Maximum Retail Price (MRP): Rs 220.00", 
        metadata={"ocr_full_text": "MRP Rs 220.00\n(Inclusive of all taxes)"}
    )
    assert res_mrp_multi.is_compliant is True

    # Rule 6(1)(d) Net Quantity standard units
    qty_rule = loader.get_rules_for_field("net_quantity")[0]
    res_qty_std = engine.evaluate_field(qty_rule, "Net Quantity: 1 L")
    assert res_qty_std.is_compliant is True

    res_qty_nonstd = engine.evaluate_field(qty_rule, "Net Qty: 1000 gms")
    assert res_qty_nonstd.is_compliant is False  # 'gms' is non-standard under Rule 8


def test_pdf_report_generation():
    """Verify binary PDF generation produces valid %PDF-1.4 format."""
    generator = PDFReportGenerator()
    dummy_summary = {
        "scan_id": "test-scan-uuid-001",
        "created_at": "2026-11-19T10:00:00Z",
        "status": "compliant",
        "overall_status": "compliant",
        "batch_number": "HN-MO-8924",
        "product": {"name": "Himalayan Harvest Mustard Oil", "brand": "Himalayan Harvest"},
        "inspector": {"name": "Inspector Vikram Sharma"},
        "declarations": [
            {
                "field_type": "mrp",
                "extracted_text": "Rs 220.00 (incl. of all taxes)",
                "is_compliant": True,
                "severity": "none",
                "rule_reference": "Rule 6(1)(f)",
            },
            {
                "field_type": "manufacturer_details",
                "extracted_text": "Himalayan Naturals Pvt. Ltd.",
                "is_compliant": True,
                "severity": "none",
                "rule_reference": "Rule 6(1)(b)",
            }
        ]
    }
    pdf_bytes = generator.generate_pdf_bytes(dummy_summary)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf_bytes[-100:]


def test_docx_report_generation():
    """Verify DOCX generation produces valid document stream."""
    dummy_summary = {
        "scan_id": "test-scan-uuid-002",
        "created_at": "2026-11-19T10:00:00Z",
        "status": "compliant",
        "batch_number": "HN-MO-8924",
        "product": {"name": "Himalayan Harvest Mustard Oil"},
        "inspector": {"name": "Inspector Vikram Sharma"},
        "declarations": []
    }
    docx_bytes = DocxReportGenerator.generate_docx_bytes(dummy_summary)
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 0
    # Valid docx (PK zip archive)
    assert docx_bytes.startswith(b"PK")
