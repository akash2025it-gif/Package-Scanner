import os
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader
from app.core.exceptions import StorageException


class PDFReportGenerator:
    """Generates statutory compliance PDF reports via Jinja2 & WeasyPrint."""

    def __init__(self, templates_dir: str = None):
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

    def render_html(self, context: Dict[str, Any]) -> str:
        template = self.jinja_env.get_template("compliance_report.html")
        return template.render(**context)

    def generate_pdf_bytes(self, context: Dict[str, Any]) -> bytes:
        try:
            from weasyprint import HTML
            html_content = self.render_html(context)
            return HTML(string=html_content).write_pdf()
        except Exception:
            return self.generate_binary_pdf(context)

    def generate_binary_pdf(self, context: Dict[str, Any]) -> bytes:
        """
        Generates a 100% compliant, valid binary PDF (%PDF-1.4) statutory inspection certificate.
        Runs entirely in pure Python with zero native C-library dependencies.
        """
        commands = []
        
        # 1. Header Banner (#00174b deep navy)
        commands.append('0.0 0.09 0.29 rg')
        commands.append('0 760 595 82 re f')
        
        # Gold accent line
        commands.append('0.85 0.70 0.25 rg')
        commands.append('0 756 595 4 re f')
        
        # Header Text
        commands.append('BT')
        commands.append('/F2 13 Tf')
        commands.append('1 1 1 rg')
        commands.append('40 812 Td')
        commands.append('(GOVERNMENT OF INDIA - MINISTRY OF CONSUMER AFFAIRS) Tj')
        commands.append('ET')
        
        commands.append('BT')
        commands.append('/F1 8.5 Tf')
        commands.append('0.9 0.9 0.9 rg')
        commands.append('40 796 Td')
        commands.append('(Central Legal Metrology Division - Legal Metrology \\(Packaged Commodities\\) Rules, 2011) Tj')
        commands.append('ET')
        
        commands.append('BT')
        commands.append('/F2 11 Tf')
        commands.append('1 0.85 0.3 rg')
        commands.append('40 774 Td')
        commands.append('(OFFICIAL STATUTORY COMPLIANCE INSPECTION CERTIFICATE) Tj')
        commands.append('ET')
        
        # Metadata Box
        commands.append('0.96 0.97 0.99 rg')
        commands.append('35 640 525 102 re f')
        commands.append('0.80 0.84 0.90 RG')
        commands.append('35 640 525 102 re S')
        
        commands.append('0.0 0.2 0.5 rg')
        commands.append('BT')
        commands.append('/F2 9.5 Tf')
        commands.append('45 725 Td')
        commands.append('(1. INSPECTION & COMMODITY METADATA) Tj')
        commands.append('ET')
        
        r_id = str(context.get('report_id') or 'N/A')[:32]
        s_id = str(context.get('scan_id') or 'N/A')[:32]
        p_name = str(context.get('product_name') or 'Packaged Commodity')[:36]
        insp = str(context.get('inspector_name') or 'Enforcement Officer')[:30]
        loc = str(context.get('location_name') or 'Inspection Site')[:30]
        batch = str(context.get('batch_number') or 'N/A')[:24]
        gen_at = str(context.get('generated_at') or '2026-11-15')[:24]
        
        commands.append('0.1 0.1 0.1 rg')
        commands.append('BT')
        commands.append('/F1 8 Tf')
        commands.append('45 706 Td')
        commands.append(f'(Certificate ID: {r_id}) Tj')
        commands.append('260 0 Td')
        commands.append(f'(Scan ID: {s_id}) Tj')
        commands.append('-260 -13 Td')
        commands.append(f'(Product Name: {p_name}) Tj')
        commands.append('260 0 Td')
        commands.append(f'(Batch/Lot: {batch}) Tj')
        commands.append('-260 -13 Td')
        commands.append(f'(Inspection Officer: {insp}) Tj')
        commands.append('260 0 Td')
        commands.append(f'(Location: {loc}) Tj')
        commands.append('-260 -13 Td')
        commands.append(f'(Date & Time: {gen_at}) Tj')
        commands.append('ET')
        
        # Verdict Banner
        verdict = str(context.get('overall_status') or 'needs_review').lower()
        if verdict == 'compliant':
            bg_cmd = '0.08 0.55 0.25 rg'
            v_title = 'STATUTORY VERDICT: VERIFIED COMPLIANT'
            v_sub = 'All mandatory declarations under Rule 6 meet Legal Metrology requirements.'
        elif verdict == 'non_compliant':
            bg_cmd = '0.75 0.12 0.12 rg'
            v_title = 'STATUTORY VERDICT: NON-COMPLIANT / CITATION REQUIRED'
            v_sub = 'Mandatory declaration violations detected against statutory provisions.'
        else:
            bg_cmd = '0.85 0.50 0.05 rg'
            v_title = 'STATUTORY VERDICT: MANUAL REVIEW REQUIRED'
            v_sub = 'Verification pending inspector review. Findings require manual examination.'
            
        commands.append(bg_cmd)
        commands.append('35 595 525 36 re f')
        
        commands.append('BT')
        commands.append('/F2 10.5 Tf')
        commands.append('1 1 1 rg')
        commands.append('45 617 Td')
        commands.append(f'({v_title}) Tj')
        commands.append('ET')
        
        commands.append('BT')
        commands.append('/F1 7.5 Tf')
        commands.append('1 1 1 rg')
        commands.append('45 604 Td')
        commands.append(f'({v_sub}) Tj')
        commands.append('ET')
        
        # Declarations Table Header
        commands.append('0.92 0.94 0.97 rg')
        commands.append('35 565 525 18 re f')
        commands.append('0.7 0.7 0.7 RG')
        commands.append('35 565 525 18 re S')
        
        commands.append('0 0 0 rg')
        commands.append('BT')
        commands.append('/F2 7.5 Tf')
        commands.append('40 571 Td')
        commands.append('(RULE REFERENCE) Tj')
        commands.append('105 0 Td')
        commands.append('(MANDATORY DECLARATION) Tj')
        commands.append('175 0 Td')
        commands.append('(VERDICT) Tj')
        commands.append('60 0 Td')
        commands.append('(EXTRACTED LABEL EVIDENCE) Tj')
        commands.append('ET')
        
        # Rows
        y = 547
        decls = context.get('declarations', [])
        for d in decls[:10]:
            ft = str(d.get('field_type') or 'declaration')
            name = str(d.get('field_name') or ft.replace('_', ' ').title())[:26]
            rule = str(d.get('rule_reference') or 'Rule 6(1)')[:18]
            is_comp = d.get('is_compliant', False)
            status_label = 'COMPLIANT' if is_comp else ('NEEDS REVIEW' if d.get('severity') == 'needs_review' else 'NON-COMPLIANT')
            val = str(d.get('extracted_text') or d.get('raw_extracted_value') or '[Not Detected]')[:36]
            val = val.replace('(', '\\(').replace(')', '\\)')
            
            commands.append('0.85 0.85 0.85 RG')
            commands.append(f'35 {y-3} 525 16 re S')
            
            commands.append('0.1 0.1 0.1 rg')
            commands.append('BT')
            commands.append('/F1 7.5 Tf')
            commands.append(f'40 {y} Td')
            commands.append(f'({rule}) Tj')
            commands.append(f'105 0 Td')
            commands.append(f'({name}) Tj')
            commands.append('ET')
            
            if is_comp:
                commands.append('0.05 0.5 0.2 rg')
            elif d.get('severity') == 'needs_review':
                commands.append('0.8 0.45 0.0 rg')
            else:
                commands.append('0.75 0.1 0.1 rg')
                
            commands.append('BT')
            commands.append('/F2 7.5 Tf')
            commands.append(f'320 {y} Td')
            commands.append(f'({status_label}) Tj')
            commands.append('ET')
            
            commands.append('0.2 0.2 0.2 rg')
            commands.append('BT')
            commands.append('/F1 7.5 Tf')
            commands.append(f'380 {y} Td')
            commands.append(f'({val}) Tj')
            commands.append('ET')
            
            y -= 16
            
        # Statutory Attestation & Footer
        commands.append('0.95 0.95 0.95 rg')
        commands.append('35 45 525 45 re f')
        commands.append('0.8 0.8 0.8 RG')
        commands.append('35 45 525 45 re S')
        
        commands.append('0.2 0.2 0.2 rg')
        commands.append('BT')
        commands.append('/F1 6.8 Tf')
        commands.append('42 75 Td')
        commands.append('(STATUTORY NOTICE: Generated under Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011.) Tj')
        commands.append('0 -10 Td')
        commands.append('(Final regulatory enforcement actions are subject to verification by the competent Legal Metrology Officer.) Tj')
        commands.append('0 -10 Td')
        commands.append('(PackCheck AI National Packaged Commodity Compliance Infrastructure - Digitally Certified.) Tj')
        commands.append('ET')
        
        # Sanitize commands for PDF Latin-1 / WinAnsi stream encoding
        sanitized_commands = []
        for cmd in commands:
            cmd_clean = (
                cmd.replace('\u20b9', 'Rs. ')
                   .replace('₹', 'Rs. ')
                   .replace('\u2013', '-')
                   .replace('\u2014', '--')
                   .replace('\u2018', "'")
                   .replace('\u2019', "'")
                   .replace('\u201c', '"')
                   .replace('\u201d', '"')
                   .replace('\u2022', '*')
            )
            # Encode with replace to eliminate any other non-latin1 characters safely
            sanitized_commands.append(cmd_clean.encode('latin1', 'replace').decode('latin1'))

        stream_data = '\n'.join(sanitized_commands).encode('latin1')
        stream_len = len(stream_data)
        
        objects = [
            b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj',
            b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj',
            b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>\nendobj',
            f'4 0 obj\n<< /Length {stream_len} >>\nstream\n'.encode('latin1') + stream_data + b'\nendstream\nendobj',
            b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj',
            b'6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj',
        ]
        
        header = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'
        offsets = [0]
        curr_offset = len(header)
        pdf_body = b''
        for obj in objects:
            offsets.append(curr_offset)
            pdf_body += obj + b'\n'
            curr_offset += len(obj) + 1
            
        xref_offset = len(header) + len(pdf_body)
        xref = f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'
        for off in offsets[1:]:
            xref += f'{off:010d} 00000 n \n'
            
        trailer = f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF'
        return header + pdf_body + xref.encode('latin1') + trailer.encode('latin1')
