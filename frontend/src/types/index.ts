export type UserRole = 'admin' | 'inspector' | 'viewer';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department?: string;
  region?: string;
  phone?: string;
  is_active: boolean;
  created_at?: string;
}

export type ComplianceStatus = 'compliant' | 'non_compliant' | 'needs_review' | 'reviewed' | 'closed' | 'failed' | 'processing';

export interface BoundingBox {
  x: number;
  y: number;
  w: number;
  h: number;
  width?: number;
  height?: number;
}

export interface BarcodeItem {
  type: 'QR_CODE' | 'BARCODE';
  format: string;
  raw_content: string;
  is_url: boolean;
  url_safety?: {
    is_url: boolean;
    is_safe: boolean;
    scheme?: string;
    domain?: string;
    reason?: string;
  };
  bounding_box: BoundingBox;
  confidence: number;
}

export interface BarcodeInfo {
  qr_detected: boolean;
  barcode_detected: boolean;
  total_detected: number;
  items: BarcodeItem[];
  summary: string;
  legal_disclaimer: string;
}

export interface DeclarationFinding {
  id: string;
  field_type: string;
  name?: string;
  extracted_text?: string | null;
  raw_extracted_value?: string | null;
  normalized_numeric_value?: number | null;
  normalized_unit?: string | null;
  bounding_box: BoundingBox;
  confidence_score: number;
  font_size_mm?: number | null;
  is_present: boolean;
  is_compliant: boolean;
  rule_reference: string;
  severity: 'none' | 'minor' | 'major' | 'critical' | 'needs_review';
  reviewer_override: boolean;
  reviewer_notes?: string | null;
  workflow_decision?: string;
  decision_method?: string;
  decision_reason?: string;
  verification_status?: string;
  verification_source?: string;
  human_decision?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  compliance_status?: 'PASS' | 'FAIL' | 'REVIEW' | 'NOT_APPLICABLE';
}

export interface ScanImage {
  id: string;
  image_url: string;
  storage_key: string;
  image_type: string;
  width_px?: number;
  height_px?: number;
  image_quality?: 'CLEAR' | 'BLURRY' | 'LOW_QUALITY' | 'FAILED';
  sharpness_score?: number;
  quality_threshold?: number;
  analysis_allowed?: boolean;
}

export interface Scan {
  id: string;
  product_id?: string | null;
  inspector_id: string;
  source: string;
  status: ComplianceStatus;
  batch_number?: string | null;
  location_name?: string | null;
  gps_coordinates?: string | null;
  metadata_json?: {
    ai_preliminary_verdict?: string;
    auto_confirmed_findings_count?: number;
    manual_review_findings_count?: number;
    total_declarations_count?: number;
    barcode_info?: BarcodeInfo;
    preprocessing?: any;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
  images: ScanImage[];
  declarations: DeclarationFinding[];
  product?: {
    id: string;
    name: string;
    brand: string;
    category: string;
    mrp: number;
    net_quantity: string;
    manufacturer_name: string;
    manufacturer_address?: string;
    barcode?: string;
  };
  inspector?: User;
}

export interface AuditLog {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  user_id?: string;
  metadata?: any;
  created_at: string;
}

export interface AnalyticsSummary {
  total_inspections: number;
  compliant_count: number;
  non_compliant_count: number;
  needs_review_count: number;
  compliance_rate: number;
  top_violations?: { field_type: string; count: number; name: string }[];
  most_common_findings?: {
    finding_name: string;
    field_type: string;
    rule_reference: string;
    affected_inspections: number;
    total_violations: number;
    severity: string;
  }[];
  regional_overview?: {
    region: string;
    total_inspections: number;
    compliant_count: number;
    non_compliant_count: number;
    violation_rate: number;
    top_violated_rule?: string;
  }[];
  product_risk_overview?: {
    category: string;
    total_inspections: number;
    non_compliant_count: number;
    compliant_count: number;
    compliance_rate?: number;
    risk_level: string;
  }[];
  dynamic_insights?: string[];
  frequently_flagged_batches?: {
    batch_number: string;
    product_name: string;
    reason: string;
    non_compliant_inspections: number;
  }[];
  monthly_trends?: { month: string; total: number; compliant: number; non_compliant: number }[];
}
