/**
 * Mock data for testing without backend
 * Matching web/src/utils/api_client.py MOCK_RECEIPTS
 */

import type { ReceiptData, MockScenario } from '@/types';

export const MOCK_RECEIPTS: MockScenario = {
  'Scenario A: Normal Office Supply': {
    receipt_id: 'DEMO-001',
    store_name: 'Alpha Stationeries',
    date: '2026-02-10 14:00',
    items: [
      { id: 1, name: 'A4 Paper (500 sheets)', unit_price: 5500, count: 2, price: 11000 },
      { id: 2, name: 'Ballpoint Pen Black', unit_price: 1200, count: 5, price: 6000 },
    ],
    total_price: 17000,
  },
  'Scenario B: Alcohol Violation': {
    receipt_id: 'DEMO-002',
    store_name: 'GS25 Convenience',
    date: '2026-02-11 19:30',
    items: [
      { id: 1, name: 'Soju (Chamisul)', unit_price: 1800, count: 3, price: 5400 },
      { id: 2, name: 'Snack', unit_price: 1500, count: 1, price: 1500 },
      { id: 3, name: 'Beer (Cass)', unit_price: 2500, count: 2, price: 5000 },
    ],
    total_price: 11900,
  },
};

/**
 * Mock audit check - matches MockAuditClient.check() logic
 */
export const mockAuditCheck = (receiptData: ReceiptData) => {
  const violations = [];
  const items = receiptData.items;

  // Check for alcohol keywords
  const alcoholKeywords = ['soju', 'beer', 'wine', 'whisky', '소주', '맥주', '주류'];
  for (const item of items) {
    const nameLower = item.name.toLowerCase();
    if (alcoholKeywords.some((kw) => nameLower.includes(kw))) {
      violations.push({
        item_id: item.id,
        reason: `Prohibited item detected: ${item.name}`,
        policy_reference: 'Financial Regulation Article 3 (Prohibition of Alcohol)',
      });
    }
  }

  // Check for suspicious time
  const dateStr = receiptData.date;
  if (dateStr.includes('23:') || dateStr.includes('00:')) {
    violations.push({
      item_id: 0,
      reason: 'Suspicious transaction time (Late Night)',
      policy_reference: 'Article 7: Midnight expenses require justification',
    });
  }

  if (violations.length === 0) {
    return {
      audit_decision: 'Pass' as const,
      violation_score: 0.05,
      violations: [],
      reasoning: 'No policy violations found in the provided data.',
    };
  } else {
    return {
      audit_decision: 'Anomaly Detected' as const,
      violation_score: 0.9,
      violations,
      reasoning: `Audit failed due to ${violations.length} potential policy violations.`,
    };
  }
};
