/**
 * TypeScript types matching backend API schema
 * server/routes/ocr.py, audit.py와 동일한 구조
 */

export interface ReceiptItem {
  id: number;
  name: string;
  unit_price: number;
  count: number;
  price: number;
}

export interface ReceiptData {
  receipt_id: string;
  store_name: string;
  date: string;
  items: ReceiptItem[];
  total_price: number;
}

export interface Violation {
  item_id: number;
  reason: string;
  policy_reference: string;
}

export interface AuditResult {
  audit_decision: 'Pass' | 'Anomaly Detected' | 'Warning';
  violation_score: number;
  violations: Violation[];
  reasoning: string;
}

export interface ConfirmPayload {
  receipt_data: ReceiptData;
  audit_result: AuditResult;
}

export interface ConfirmResponse {
  status: string;
  pdf_url: string;
  pdf_data?: string; // base64 encoded
  filename?: string;
}

// Mock scenarios (matching web/src/utils/api_client.py)
export interface MockScenario {
  [key: string]: ReceiptData;
}

// API error response
export interface APIError {
  detail?: string;
  message?: string;
}
