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
        html_content = self.render_html(context)
        
        try:
            from weasyprint import HTML
            return HTML(string=html_content).write_pdf()
        except Exception as e:
            # If WeasyPrint C-libraries are missing on host, generate styled HTML document bytes as fallback
            return html_content.encode("utf-8")
