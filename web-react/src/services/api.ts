/**
 * API Client for communicating with FastAPI backend
 * Equivalent to web/src/utils/api_client.py
 */

import axios, { AxiosError } from 'axios';
import type { ReceiptData, AuditResult, ConfirmPayload, ConfirmResponse, APIError, RulesResponse } from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error handler
const handleError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<APIError>;
    const message = axiosError.response?.data?.detail ||
                   axiosError.response?.data?.message ||
                   axiosError.message;
    throw new Error(message);
  }
  throw error;
};

/**
 * OCR API - POST /api/v1/ocr/extract
 */
export const ocrAPI = {
  extract: async (file: File): Promise<ReceiptData> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post<ReceiptData>('/api/v1/ocr/extract', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },
};

/**
 * Audit API - POST /api/v1/audit/check, /confirm
 */
export const auditAPI = {
  check: async (receiptData: ReceiptData): Promise<AuditResult> => {
    try {
      const response = await api.post<AuditResult>('/api/v1/audit/check', receiptData);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  confirm: async (receiptData: ReceiptData, auditResult: AuditResult): Promise<ConfirmResponse> => {
    try {
      const payload: ConfirmPayload = {
        receipt_data: receiptData,
        audit_result: auditResult,
      };

      const response = await api.post<ConfirmResponse>('/api/v1/audit/confirm', payload);

      // Backend returns base64 pdf_data, filename extracted from pdf_url
      // (백엔드가 이미 처리해서 보내므로 프론트엔드에서는 그대로 사용)
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  getRules: async (): Promise<RulesResponse> => {
    try {
      const response = await api.get<RulesResponse>('/api/v1/audit/rules');
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  batchConfirm: async (receipts: { receiptData: ReceiptData; auditResult: AuditResult }[]): Promise<ConfirmResponse> => {
    try {
      const payload = {
        receipts: receipts.map(r => ({
          receipt_data: r.receiptData,
          audit_result: r.auditResult,
        }))
      };

      const response = await api.post<ConfirmResponse>('/api/v1/audit/batch-confirm', payload);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  uploadRules: async (file?: File, text?: string): Promise<{ status: string; message: string }> => {
    try {
      const formData = new FormData();
      if (file) formData.append('file', file);
      if (text) formData.append('text', text);

      const response = await api.post<{ status: string; message: string }>('/api/v1/audit/upload-rules', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  deleteRule: async (ruleId: string): Promise<{ status: string; message: string }> => {
    try {
      const response = await api.delete<{ status: string; message: string }>(`/api/v1/audit/rules/${ruleId}`);
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },

  updateRule: async (ruleId: string, content: string): Promise<{ status: string; message: string }> => {
    try {
      const response = await api.put<{ status: string; message: string }>(`/api/v1/audit/rules/${ruleId}`, { content });
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },
};

/**
 * Health Check
 */
export const healthAPI = {
  check: async (): Promise<{ status: string }> => {
    try {
      const response = await api.get<{ status: string }>('/health');
      return response.data;
    } catch (error) {
      return handleError(error);
    }
  },
};
