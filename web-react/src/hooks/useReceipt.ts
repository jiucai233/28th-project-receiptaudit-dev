/**
 * Custom hook for receipt state management
 * Equivalent to Streamlit's session_state
 */

import { useState } from 'react';
import type { ReceiptData, AuditResult } from '@/types';

export const useReceipt = () => {
  const [receiptData, setReceiptData] = useState<ReceiptData | null>(null);
  const [auditResult, setAuditResult] = useState<AuditResult | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setReceiptData(null);
    setAuditResult(null);
    setCurrentStep(1);
    setError(null);
  };

  return {
    receiptData,
    setReceiptData,
    auditResult,
    setAuditResult,
    currentStep,
    setCurrentStep,
    isLoading,
    setIsLoading,
    error,
    setError,
    reset,
  };
};
