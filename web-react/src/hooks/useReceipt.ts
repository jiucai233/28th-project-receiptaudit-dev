/**
 * Custom hook for receipt state management
 * Equivalent to Streamlit's session_state
 */

import { useState, useCallback } from 'react';
import type { ReceiptItemState } from '@/types';

export const useReceipt = () => {
  const [receipts, setReceipts] = useState<ReceiptItemState[]>([]);
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const addReceipts = useCallback((newFiles: File[]) => {
    const newItems: ReceiptItemState[] = newFiles.map((file) => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      receiptData: null,
      auditResult: null,
      status: 'pending',
      error: null,
    }));

    setReceipts((prev) => [...prev, ...newItems]);

    // Generate previews
    newItems.forEach((item) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setReceipts((prev) =>
          prev.map((r) =>
            r.id === item.id ? { ...r, preview: e.target?.result as string } : r
          )
        );
      };
      if (item.file) reader.readAsDataURL(item.file);
    });
  }, []);

  const updateReceipt = useCallback((id: string, updates: Partial<ReceiptItemState>) => {
    setReceipts((prev) =>
      prev.map((r) => (r.id === id ? { ...r, ...updates } : r))
    );
  }, []);

  const removeReceipt = useCallback((id: string) => {
    setReceipts((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const reset = () => {
    setReceipts([]);
    setCurrentStep(1);
    setError(null);
  };

  return {
    receipts,
    setReceipts,
    addReceipts,
    updateReceipt,
    removeReceipt,
    currentStep,
    setCurrentStep,
    isLoading,
    setIsLoading,
    error,
    setError,
    reset,
  };
};
