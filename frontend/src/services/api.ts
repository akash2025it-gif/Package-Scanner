import { User, Scan, ScanImage, DeclarationFinding, AuditLog, AnalyticsSummary } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

class ApiClient {
  private getHeaders(isFormData = false): HeadersInit {
    const headers: Record<string, string> = {};
    const token = localStorage.getItem('packcheck_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  private async handleResponse<T>(res: Response): Promise<T> {
    if (res.status === 401) {
      let errorMsg = 'Session expired or unauthorized. Please log in.';
      try {
        const errJson = await res.json();
        errorMsg = errJson.error?.message || errJson.message || errorMsg;
      } catch {
        // use default error message
      }

      // If the 401 is from the login endpoint itself, report credential error without destroying session state
      if (res.url.endsWith('/auth/login')) {
        throw new Error(errorMsg || 'Invalid email or password');
      }

      // Authoritative token verification endpoints (/auth/me or /auth/refresh)
      const isCoreAuthEndpoint = res.url.includes('/auth/me') || res.url.includes('/auth/refresh');

      if (isCoreAuthEndpoint) {
        // Genuine token expiration or revocation: clean up session once without repeating events
        if (localStorage.getItem('packcheck_token')) {
          localStorage.removeItem('packcheck_token');
          localStorage.removeItem('packcheck_user');
          window.dispatchEvent(new Event('auth:unauthorized'));
        }
      } else {
        // Auxiliary endpoints: fail the specific call without blowing away the active session
        console.warn(`[PackCheck API] Auxiliary endpoint returned 401: ${res.url}`);
      }

      throw new Error(errorMsg);
    }

    let body: any;
    try {
      body = await res.json();
    } catch {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    if (!res.ok || body.success === false) {
      const msg = body.error?.message || body.message || `Request failed with status ${res.status}`;
      throw new Error(msg);
    }

    return body.data !== undefined ? body.data : body;
  }

  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    return await this.handleResponse(res);
  }

  async getCurrentUser(): Promise<User> {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: this.getHeaders(),
      });
      return await this.handleResponse(res);
    } catch (err) {
      const stored = localStorage.getItem('packcheck_user');
      if (stored) {
        return JSON.parse(stored);
      }
      throw err;
    }
  }

  async getScans(params?: { status?: string; search?: string; page?: number; limit?: number }): Promise<{ items: Scan[]; total: number }> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.page) query.set('page', String(params.page));
    if (params?.limit) query.set('limit', String(params.limit || 50));
    
    const res = await fetch(`${API_BASE_URL}/scans?${query.toString()}`, {
      headers: this.getHeaders(),
    });
    const data = await this.handleResponse<any>(res);
    return {
      items: data.items || data || [],
      total: data.total || (Array.isArray(data) ? data.length : 0),
    };
  }

  async getScan(id: string): Promise<Scan> {
    const res = await fetch(`${API_BASE_URL}/scans/${id}`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async createScan(payload: {
    source: string;
    product_id?: string;
    batch_number?: string;
    location_name?: string;
    gps_coordinates?: string;
  }): Promise<Scan> {
    const res = await fetch(`${API_BASE_URL}/scans`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });
    return this.handleResponse(res);
  }

  async checkImageQuality(file: File): Promise<{
    image_quality: 'CLEAR' | 'BLURRY' | 'LOW_QUALITY' | 'FAILED';
    sharpness_score: number;
    threshold: number;
    can_analyze: boolean;
    message: string;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE_URL}/scans/quality-check`, {
      method: 'POST',
      headers: this.getHeaders(true),
      body: formData,
    });
    return this.handleResponse(res);
  }

  async uploadScanImage(scanId: string, file: File, imageType = 'front'): Promise<ScanImage[]> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('files', file);
    formData.append('image_type', imageType);
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/images`, {
      method: 'POST',
      headers: this.getHeaders(true),
      body: formData,
    });
    return this.handleResponse(res);
  }

  async analyzeScan(scanId: string): Promise<{ job_id: string; status: string; message: string }> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/analyze`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async reviewDeclaration(
    scanId: string,
    declId: string,
    payload: { action: 'confirm' | 'reject' | 'override'; reviewer_notes?: string }
  ): Promise<DeclarationFinding> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/declarations/${declId}/review`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });
    return this.handleResponse(res);
  }

  async updateDeclaration(
    scanId: string,
    declId: string,
    payload: { extracted_text?: string; is_compliant?: boolean; notes?: string }
  ): Promise<DeclarationFinding> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/declarations/${declId}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });
    return this.handleResponse(res);
  }

  async finalizeScan(scanId: string): Promise<Scan> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/finalize`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async closeScan(scanId: string): Promise<Scan> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/close`, {
      method: 'POST',
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async getAuditTrail(scanId: string): Promise<AuditLog[]> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/audit-trail`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async generateReport(scanId: string, notes?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/report`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ notes }),
    });
    return this.handleResponse(res);
  }

  async getScanReport(scanId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/scans/${scanId}/report`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  getReportPdfUrl(reportId: string): string {
    return `${API_BASE_URL}/reports/${reportId}/pdf`;
  }

  getReportDocxUrl(reportId: string): string {
    return `${API_BASE_URL}/reports/${reportId}/docx`;
  }

  async downloadReportPdf(reportId: string, filename?: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/reports/${reportId}/pdf`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      let errMsg = `Failed to download PDF report (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errMsg = errJson.error?.message || errJson.message || errMsg;
      } catch {
        // ignore json parse error
      }
      throw new Error(errMsg);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `PackCheck_Compliance_Report_${reportId.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  async downloadReportDocx(reportId: string, filename?: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/reports/${reportId}/docx`, {
      headers: this.getHeaders(),
    });
    if (!res.ok) {
      let errMsg = `Failed to download DOCX dossier (HTTP ${res.status})`;
      try {
        const errJson = await res.json();
        errMsg = errJson.error?.message || errJson.message || errMsg;
      } catch {
        // ignore json parse error
      }
      throw new Error(errMsg);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `PackCheck_Compliance_Dossier_${reportId.slice(0, 8)}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const res = await fetch(`${API_BASE_URL}/analytics/summary`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async getAutomationConfig(): Promise<{ auto_confirm_threshold: number }> {
    const res = await fetch(`${API_BASE_URL}/automation-config`, {
      headers: this.getHeaders(),
    });
    return this.handleResponse(res);
  }

  async updateAutomationConfig(threshold: number): Promise<{ auto_confirm_threshold: number }> {
    const res = await fetch(`${API_BASE_URL}/automation-config`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify({ auto_confirm_threshold: threshold }),
    });
    return this.handleResponse(res);
  }
}

export const api = new ApiClient();
