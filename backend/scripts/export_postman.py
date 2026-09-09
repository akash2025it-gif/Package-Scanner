import json
import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


def export_openapi_and_postman():
    output_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
    
    # 1. Export OpenAPI JSON
    openapi_schema = app.openapi()
    openapi_file = os.path.join(output_dir, "openapi.json")
    with open(openapi_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"[SUCCESS] Exported OpenAPI specification to: {openapi_file}")

    # 2. Build Postman Collection v2.1
    postman_collection = {
        "info": {
            "name": "PackCheck API Collection",
            "_postman_id": "packcheck-lmpc-scanner-v1",
            "description": "Comprehensive Postman collection for PackCheck (Legal Metrology Compliance Scanner APIs).",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000/api/v1", "type": "string"},
            {"key": "auth_token", "value": "", "type": "string"},
            {"key": "scan_id", "value": "", "type": "string"},
        ],
        "item": [
            {
                "name": "Authentication",
                "item": [
                    {
                        "name": "1. Login (Email + Password)",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Content-Type", "value": "application/json"}],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {"email": "inspector.sharma@packcheck.gov.in", "password": "inspector123"},
                                    indent=2,
                                ),
                            },
                            "url": {"raw": "{{base_url}}/auth/login", "host": ["{{base_url}}"], "path": ["auth", "login"]},
                        },
                    },
                    {
                        "name": "2. Get Current User Profile (/auth/me)",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auth_token}}"}],
                            "url": {"raw": "{{base_url}}/auth/me", "host": ["{{base_url}}"], "path": ["auth", "me"]},
                        },
                    },
                ],
            },
            {
                "name": "Scans & AI Pipeline",
                "item": [
                    {
                        "name": "1. Create New Scan",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Content-Type", "value": "application/json"},
                                {"key": "Authorization", "value": "Bearer {{auth_token}}"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps(
                                    {
                                        "source": "physical_store",
                                        "location_name": "Smart Bazaar, Sector 18, Noida",
                                        "product_data": {
                                            "name": "Tata Salt Vacuum Evaporated 1kg",
                                            "brand": "Tata Salt",
                                            "category": "Salt & Spices",
                                            "country_of_origin": "India",
                                        },
                                    },
                                    indent=2,
                                ),
                            },
                            "url": {"raw": "{{base_url}}/scans", "host": ["{{base_url}}"], "path": ["scans"]},
                        },
                    },
                    {
                        "name": "2. Trigger AI Analysis Pipeline",
                        "request": {
                            "method": "POST",
                            "header": [{"key": "Authorization", "value": "Bearer {{auth_token}}"}],
                            "url": {
                                "raw": "{{base_url}}/scans/{{scan_id}}/analyze",
                                "host": ["{{base_url}}"],
                                "path": ["scans", "{{scan_id}}", "analyze"],
                            },
                        },
                    },
                    {
                        "name": "3. Get Scan Details & Verdicts",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auth_token}}"}],
                            "url": {
                                "raw": "{{base_url}}/scans/{{scan_id}}",
                                "host": ["{{base_url}}"],
                                "path": ["scans", "{{scan_id}}"],
                            },
                        },
                    },
                ],
            },
            {
                "name": "Reports",
                "item": [
                    {
                        "name": "1. Generate Compliance Report (PDF + DOCX)",
                        "request": {
                            "method": "POST",
                            "header": [
                                {"key": "Content-Type", "value": "application/json"},
                                {"key": "Authorization", "value": "Bearer {{auth_token}}"},
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": json.dumps({"notes": "Inspected on-site during routine enforcement drive."}, indent=2),
                            },
                            "url": {
                                "raw": "{{base_url}}/scans/{{scan_id}}/report",
                                "host": ["{{base_url}}"],
                                "path": ["scans", "{{scan_id}}", "report"],
                            },
                        },
                    }
                ],
            },
            {
                "name": "Analytics & Dashboard",
                "item": [
                    {
                        "name": "1. Summary KPIs",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auth_token}}"}],
                            "url": {"raw": "{{base_url}}/analytics/summary", "host": ["{{base_url}}"], "path": ["analytics", "summary"]},
                        },
                    },
                    {
                        "name": "2. Regional Heatmap",
                        "request": {
                            "method": "GET",
                            "header": [{"key": "Authorization", "value": "Bearer {{auth_token}}"}],
                            "url": {"raw": "{{base_url}}/analytics/region-heatmap", "host": ["{{base_url}}"], "path": ["analytics", "region-heatmap"]},
                        },
                    },
                ],
            },
        ],
    }

    postman_file = os.path.join(output_dir, "packcheck_postman_collection.json")
    with open(postman_file, "w", encoding="utf-8") as f:
        json.dump(postman_collection, f, indent=2)
    print(f"[SUCCESS] Exported Postman collection to: {postman_file}")


if __name__ == "__main__":
    export_openapi_and_postman()
