import io
import time
import httpx
from PIL import Image

def main():
    base_url = 'http://127.0.0.1:8000/api/v1'
    client = httpx.Client(base_url=base_url, timeout=15.0)

    print("=================================================================")
    print(" ENFORCEMENT INTELLIGENCE DASHBOARD — LIVE SERVER VERIFICATION")
    print("=================================================================")

    # 1. Login as Admin
    login_res = client.post('/auth/login', json={'email': 'admin@packcheck.gov.in', 'password': 'admin123'})
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    admin_token = login_res.json()['data']['access_token']
    admin_headers = {'Authorization': f'Bearer {admin_token}'}
    print("[1] Admin login successful.")

    # 2. Fetch Dashboard Analytics Summary
    summary_res = client.get('/analytics/summary', headers=admin_headers)
    assert summary_res.status_code == 200, f"Summary failed: {summary_res.text}"
    summary = summary_res.json()['data']
    print("\n[2] Live Dashboard Summary KPIs:")
    print(f"    - Total Inspections: {summary['total_inspections']}")
    print(f"    - Compliant: {summary['compliant_count']}")
    print(f"    - Non-Compliant: {summary['non_compliant_count']}")
    print(f"    - Needs Manual Review: {summary['needs_review_count']}")
    print(f"    - Compliance Rate: {summary['compliance_rate']}%")
    print(f"    - Violation Rate: {summary['violation_rate']}%")
    print(f"    - Finalized Count: {summary['finalized_count']}")
    print(f"    - Dynamic Insights: {summary['dynamic_insights']}")

    assert "total_inspections" in summary
    assert "compliance_rate" in summary
    assert "most_common_findings" in summary
    assert "product_risk_overview" in summary
    assert "attention_inspections" in summary
    assert "officer_activity" in summary
    assert "regional_overview" in summary

    # 3. Test Inspection Trends Endpoint
    trend_res = client.get('/analytics/inspection-trends?days=30', headers=admin_headers)
    assert trend_res.status_code == 200, f"Trends failed: {trend_res.text}"
    trends = trend_res.json()['data']
    print(f"\n[3] Inspection Activity Trends: {len(trends)} day buckets retrieved.")

    # 4. Test Common Violations Ranking Endpoint
    viol_res = client.get('/analytics/violations', headers=admin_headers)
    assert viol_res.status_code == 200, f"Violations failed: {viol_res.text}"
    violations = viol_res.json()['data']
    print(f"[4] Most Common Compliance Findings ({len(violations)} finding categories):")
    for v in violations[:3]:
        print(f"    * {v['finding_name']}: {v['affected_inspections']} scan(s) affected ({v['percentage_of_non_compliant']}%)")

    # 5. Test Product Risk Overview Endpoint
    risk_res = client.get('/analytics/product-risk', headers=admin_headers)
    assert risk_res.status_code == 200, f"Product risk failed: {risk_res.text}"
    risks = risk_res.json()['data']
    print(f"[5] Product Risk Overview ({len(risks)} categories):")
    for r in risks[:3]:
        print(f"    * {r['category']}: Total={r['total_inspections']}, Non-Comp={r['non_compliant_count']}, Risk={r['risk_level']}")

    # 6. Test Attention Inspections Queue
    att_res = client.get('/analytics/attention', headers=admin_headers)
    assert att_res.status_code == 200, f"Attention failed: {att_res.text}"
    att_items = att_res.json()['data']
    print(f"[6] Inspections Requiring Attention: {len(att_items)} priority scans in queue.")
    for item in att_items[:2]:
        print(f"    * #{item['id'][:8]} - {item['product_name']} | Status: {item['status']} | Reason: {item['attention_reason']}")

    # 7. Test Officer Activity and Regional Surveillance
    off_res = client.get('/analytics/officer-activity', headers=admin_headers)
    assert off_res.status_code == 200, f"Officer activity failed: {off_res.text}"
    reg_res = client.get('/analytics/region-heatmap', headers=admin_headers)
    assert reg_res.status_code == 200, f"Regional overview failed: {reg_res.text}"
    print(f"[7] Officer Activity: {len(off_res.json()['data'])} officers tracked.")
    print(f"    Regional Surveillance: {len(reg_res.json()['data'])} zones tracked.")

    # 8. Test Dynamic Multi-Filtering
    print("\n[8] Testing Multi-Dimensional Filter Combinations:")
    f_7d = client.get('/analytics/summary?days=7', headers=admin_headers).json()['data']
    print(f"    - Filter 'Last 7 Days': {f_7d['total_inspections']} scans in scope")
    f_noncomp = client.get('/analytics/summary?status=non_compliant', headers=admin_headers).json()['data']
    print(f"    - Filter 'Non-Compliant Status': {f_noncomp['total_inspections']} scans in scope")
    if summary['available_categories']:
        cat = summary['available_categories'][0]
        f_cat = client.get(f'/analytics/summary?category={cat}', headers=admin_headers).json()['data']
        print(f"    - Filter 'Category: {cat}': {f_cat['total_inspections']} scans in scope")

    # 9. Create a New Inspection Scan, Analyze and Finalize it
    print("\n[9] Testing Dynamic Scan Creation, AI Analysis, and Finalization Workflow:")
    scan_res = client.post('/scans', json={
        'source': 'physical_store',
        'location_name': 'Supermarket Sector 29, Gurgaon',
        'product_data': {
            'name': 'Golden Almond Crunch Cookies 250g',
            'brand': 'CrunchyBites',
            'category': 'Packaged Bakery & Cookies',
            'country_of_origin': 'India'
        }
    }, headers=admin_headers)
    assert scan_res.status_code == 201, f"Scan creation failed: {scan_res.text}"
    new_scan_id = scan_res.json()['data']['id']
    print(f"    - Created New Scan ID: {new_scan_id}")

    # Upload Label Image
    buf = io.BytesIO()
    img = Image.new('RGB', (1000, 1400), color=(230, 210, 180))
    img.save(buf, format='JPEG')
    buf.seek(0)
    upload_res = client.post(
        f'/scans/{new_scan_id}/images',
        files={'files': ('cookies_label.jpg', buf.getvalue(), 'image/jpeg')},
        headers=admin_headers
    )
    assert upload_res.status_code == 200, "Image upload failed"

    # Analyze Scan
    analyze_res = client.post(f'/scans/{new_scan_id}/analyze', headers=admin_headers)
    assert analyze_res.status_code == 200, "Analyze failed"
    time.sleep(1.5)

    # Verify Scan details
    detail_res = client.get(f'/scans/{new_scan_id}', headers=admin_headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()['data']['declarations']
    print(f"    - AI Analysis completed: {len(decls)} declarations extracted.")

    # Finalize as Non-Compliant
    fin_res = client.post(f'/scans/{new_scan_id}/finalize', json={
        'final_decision': 'non_compliant',
        'remarks': 'Mandatory USP declaration missing on primary display panel.'
    }, headers=admin_headers)
    assert fin_res.status_code == 200, f"Finalize failed: {fin_res.text}"
    print(f"    - Finalized inspection #{new_scan_id[:8]} as NON_COMPLIANT with statutory officer remarks.")

    # 10. Verify Dashboard Statistics Updated
    summary_after = client.get('/analytics/summary', headers=admin_headers).json()['data']
    print(f"\n[10] Updated Dashboard Statistics:")
    print(f"     - Total Inspections: {summary_after['total_inspections']} (previously {summary['total_inspections']})")
    print(f"     - Non-Compliant: {summary_after['non_compliant_count']} (previously {summary['non_compliant_count']})")
    print(f"     - Compliance Rate: {summary_after['compliance_rate']}%")
    print(f"     - Violation Rate: {summary_after['violation_rate']}%")
    assert summary_after['total_inspections'] == summary['total_inspections'] + 1
    assert summary_after['non_compliant_count'] == summary['non_compliant_count'] + 1

    # 11. Test RBAC Permissions across Inspector, Reviewer, Viewer
    print("\n[11] Verifying RBAC Access across All Roles:")
    for role, email, pwd in [
        ('inspector', 'inspector.sharma@packcheck.gov.in', 'inspector123'),
        ('reviewer', 'reviewer.patel@packcheck.gov.in', 'reviewer123'),
        ('viewer', 'viewer@packcheck.gov.in', 'viewer123'),
    ]:
        u_login = client.post('/auth/login', json={'email': email, 'password': pwd})
        assert u_login.status_code == 200, f"{role} login failed"
        u_token = u_login.json()['data']['access_token']
        u_headers = {'Authorization': f'Bearer {u_token}'}

        u_summary = client.get('/analytics/summary', headers=u_headers)
        assert u_summary.status_code == 200, f"{role} summary failed"

        u_trends = client.get('/analytics/inspection-trends', headers=u_headers)
        assert u_trends.status_code == 200, f"{role} trends failed"

        u_att = client.get('/analytics/attention', headers=u_headers)
        assert u_att.status_code == 200, f"{role} attention failed"

        # Verify viewer cannot modify user accounts or finalize scans
        if role == 'viewer':
            u_fin = client.post(f'/scans/{new_scan_id}/finalize', json={'final_decision': 'compliant', 'remarks': 'Viewer try'}, headers=u_headers)
            assert u_fin.status_code == 403, "Viewer was able to finalize scan!"
            u_users = client.get('/users', headers=u_headers)
            assert u_users.status_code == 403, "Viewer was able to access /users!"

        print(f"     * Role '{role.upper()}' verified successfully with appropriate permissions.")

    # 12. Verify HTML Page Assets
    print("\n[12] Verifying Static Web Pages:")
    for page in ['/dashboard', '/analysis', '/scan/new', '/products-ui', '/enforcement', '/login']:
        p_res = client.get(page.replace('/api/v1', ''))
        assert p_res.status_code == 200, f"Page {page} returned {p_res.status_code}"
        assert len(p_res.text) > 500
        print(f"     * Route '{page}' serving HTML ({len(p_res.text)} bytes)")

    print("\n=================================================================")
    print(" [SUCCESS] ALL 12 ENFORCEMENT INTELLIGENCE VERIFICATIONS PASSED!")
    print("=================================================================\n")

if __name__ == '__main__':
    main()
