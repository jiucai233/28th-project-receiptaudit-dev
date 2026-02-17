/**
 * Main App Component
 * Equivalent to web/app.py
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Upload, PenLine, BarChart3, ClipboardList, Target,
  RotateCcw, AlertTriangle, Moon, Sun, Receipt,
  Search, Rocket, FileDown, Loader2, ArrowRight,
} from 'lucide-react';
import { UploadStep } from './components/UploadStep';
import { DataEditor } from './components/DataEditor';
import { AuditResults } from './components/AuditResults';
import { useReceipt } from './hooks/useReceipt';
import { ocrAPI, auditAPI } from './services/api';
import { MOCK_RECEIPTS } from './services/mockData';
import type { ReceiptData } from './types';

/** Subtle ripple on button click */
function createRipple(e: React.MouseEvent<HTMLButtonElement>) {
  const button = e.currentTarget;
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = e.clientX - rect.left - size / 2;
  const y = e.clientY - rect.top - size / 2;

  const ripple = document.createElement('span');
  ripple.className = 'ripple-effect';
  ripple.style.width = ripple.style.height = `${size}px`;
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  button.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

function App() {
  const {
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
  } = useReceipt();

  const [activeTab, setActiveTab] = useState(0);
  const [dark, setDark] = useState(false);

  // Dark mode toggle
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  // OCR Extract handler
  const handleExtract = useCallback(async (file: File): Promise<ReceiptData> => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await ocrAPI.extract(file);
      setReceiptData(data);
      setCurrentStep(2);
      setActiveTab(1);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'OCR 처리 실패';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [setIsLoading, setError, setReceiptData, setCurrentStep]);

  // Audit Check handler
  const handleAuditCheck = async () => {
    if (!receiptData) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await auditAPI.check(receiptData);
      setAuditResult(result);
      setCurrentStep(3);
    } catch (err) {
      const message = err instanceof Error ? err.message : '감사 실패';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // PDF Confirm handler
  const handleConfirm = async () => {
    if (!receiptData || !auditResult) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await auditAPI.confirm(receiptData, auditResult);

      if (response.status === 'success' && response.pdf_data) {
        const byteCharacters = atob(response.pdf_data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: 'application/pdf' });

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = response.filename || `audit_report_${receiptData.receipt_id}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        alert('PDF 다운로드 완료!');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'PDF 생성 실패';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Quick demo scenario loader
  const loadScenario = (scenarioName: string) => {
    const data = MOCK_RECEIPTS[scenarioName];
    if (data) {
      setReceiptData(data);
      setAuditResult(null);
      setCurrentStep(2);
      setActiveTab(1);
    }
  };

  const steps = [
    { step: 1, label: '영수증 업로드', icon: Upload },
    { step: 2, label: '데이터 편집 & 감사', icon: PenLine },
    { step: 3, label: '최종 결과', icon: BarChart3 },
  ];

  const tabData = [
    { label: '업로드', icon: Upload },
    { label: '편집 & 감사', icon: PenLine },
    { label: '최종 결과', icon: BarChart3 },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      {/* Header - Glass Morphism */}
      <header className="glass sticky top-0 z-50 shadow-lg border-b border-primary-200/30 dark:border-slate-700/50">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl flex items-center justify-center shadow-md">
                <Receipt className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gradient">Transparent-Audit</h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">스마트 영수증 감사 시스템</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setDark(!dark)}
                onMouseDown={createRipple}
                className="p-2.5 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-all relative overflow-hidden"
                aria-label="Toggle dark mode"
              >
                {dark ? <Sun className="w-5 h-5 text-yellow-400" /> : <Moon className="w-5 h-5 text-gray-600" />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {error && (
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 text-red-800 dark:text-red-300 px-6 py-4 rounded-lg shadow-sm animate-fadeIn">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <p className="font-semibold">오류 발생</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex max-w-[1600px] mx-auto">
        {/* Sidebar - Glass Morphism */}
        <aside className="w-72 glass p-6 shadow-lg min-h-screen">
          <div className="sticky top-24">
            <h2 className="font-bold text-lg mb-6 text-gray-800 dark:text-gray-200 flex items-center gap-2">
              <span className="w-8 h-8 bg-primary-100 dark:bg-primary-900/50 rounded-lg flex items-center justify-center">
                <ClipboardList className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </span>
              진행 단계
            </h2>
            <ul className="space-y-3 mb-8">
              {steps.map(({ step, label, icon: Icon }) => (
                <li
                  key={step}
                  className={`step-indicator flex items-center gap-3 px-4 py-3 rounded-lg cursor-pointer ${
                    currentStep === step
                      ? 'active bg-primary-50 dark:bg-primary-900/30 border-l-4 border-primary-600 font-semibold text-primary-700 dark:text-primary-400'
                      : currentStep > step
                      ? 'text-green-600 dark:text-green-400 hover:bg-gray-50 dark:hover:bg-slate-700'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-sm">
                    {step}. {label}
                  </span>
                  {currentStep > step && (
                    <span className="ml-auto text-green-500 text-xs">&#10003;</span>
                  )}
                </li>
              ))}
            </ul>

            <div className="border-t border-gray-200 dark:border-slate-700 pt-6 mb-6">
              <h3 className="font-semibold mb-3 text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <Target className="w-4 h-4" /> Quick Demo
              </h3>
              <div className="space-y-2">
                {Object.keys(MOCK_RECEIPTS).map((scenario) => (
                  <button
                    key={scenario}
                    onClick={() => loadScenario(scenario)}
                    onMouseDown={createRipple}
                    className="w-full text-left text-sm px-4 py-2.5 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-900/20 border border-gray-200 dark:border-slate-600 hover:border-primary-300 dark:hover:border-primary-600 transition-all duration-200 text-gray-700 dark:text-gray-300 hover:text-primary-700 dark:hover:text-primary-400 relative overflow-hidden"
                  >
                    {scenario.replace('Scenario ', '')}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={reset}
              onMouseDown={createRipple}
              className="w-full bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-gray-300 px-4 py-2.5 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-all duration-200 font-medium flex items-center justify-center gap-2 relative overflow-hidden"
            >
              <RotateCcw className="w-4 h-4" /> Reset
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8">
          <div className="max-w-6xl mx-auto">
            {/* Tabs */}
            <div className="flex gap-2 mb-8 glass rounded-xl p-2 shadow-sm">
              {tabData.map(({ label, icon: Icon }, idx) => (
                <button
                  key={idx}
                  onClick={() => setActiveTab(idx)}
                  onMouseDown={createRipple}
                  className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 relative overflow-hidden ${
                    activeTab === idx
                      ? 'bg-primary-600 text-white shadow-md scale-[1.02]'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-slate-700 hover:text-gray-900 dark:hover:text-gray-200'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            {activeTab === 0 && <UploadStep onUploadSuccess={setReceiptData} onExtract={handleExtract} />}

            {activeTab === 1 && (
              <div className="space-y-6">
                {receiptData ? (
                  <>
                    <DataEditor data={receiptData} onChange={setReceiptData} />

                    <div className="flex gap-4 justify-center mt-8">
                      <button
                        onClick={handleAuditCheck}
                        onMouseDown={createRipple}
                        disabled={isLoading}
                        className="btn-success px-10 py-4 text-lg flex items-center gap-2"
                      >
                        {isLoading ? (
                          <><Loader2 className="w-5 h-5 animate-spin" /> AI 감사 중...</>
                        ) : (
                          <><Rocket className="w-5 h-5" /> AI 감사 실행</>
                        )}
                      </button>
                    </div>

                    {auditResult && (
                      <div className="mt-8 animate-fadeIn">
                        <AuditResults result={auditResult} />
                        <div className="text-center mt-6">
                          <button
                            onClick={() => setActiveTab(2)}
                            onMouseDown={createRipple}
                            className="btn-primary px-8 py-3 flex items-center gap-2 mx-auto"
                          >
                            다음 단계로 <ArrowRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-center py-12">
                    <div className="inline-block p-8 bg-white dark:bg-slate-800 rounded-xl shadow-card">
                      <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-500 dark:text-gray-400 text-lg">먼저 영수증을 업로드해주세요</p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 2 && (
              <div className="space-y-8">
                {auditResult ? (
                  <>
                    <AuditResults result={auditResult} compact />
                    <div className="border-t border-gray-200 dark:border-slate-700 pt-8"></div>
                    <div className="text-center">
                      <button
                        onClick={handleConfirm}
                        onMouseDown={createRipple}
                        disabled={isLoading}
                        className="btn-success px-10 py-4 text-lg flex items-center gap-2 mx-auto"
                      >
                        {isLoading ? (
                          <><Loader2 className="w-5 h-5 animate-spin" /> PDF 생성 중...</>
                        ) : (
                          <><FileDown className="w-5 h-5" /> PDF 보고서 생성 및 다운로드</>
                        )}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="text-center py-12">
                    <div className="inline-block p-8 bg-white dark:bg-slate-800 rounded-xl shadow-card">
                      <Search className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="text-gray-500 dark:text-gray-400 text-lg">먼저 감사를 실행해주세요</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;
