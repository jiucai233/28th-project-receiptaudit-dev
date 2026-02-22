/**
 * Main App Component
 * Equivalent to web/app.py
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Upload, PenLine, BarChart3, ClipboardList, Target,
  RotateCcw, AlertTriangle, Moon, Sun, Receipt,
  Search, Rocket, FileDown, Loader2, ArrowRight,
  Layers, ChevronRight, FileText, Image as ImageIcon,
  BookOpen, ChevronDown, ChevronUp, Database, ShieldAlert
} from 'lucide-react';
import { UploadStep } from './components/UploadStep';
import { DataEditor } from './components/DataEditor';
import { AuditResults } from './components/AuditResults';
import { RuleEditorModal } from './components/RuleEditorModal';
import { useReceipt } from './hooks/useReceipt';
import { ocrAPI, auditAPI } from './services/api';
import { MOCK_RECEIPTS } from './services/mockData';
import type { ReceiptData, ReceiptItemState, RulesResponse } from './types';

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
  } = useReceipt();

  const [activeTab, setActiveTab] = useState(0);
  const [dark, setDark] = useState(false);
  const [selectedReceiptId, setSelectedReceiptId] = useState<string | null>(null);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);

  // Dark mode toggle
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
  }, [dark]);

  // OCR Extract handler for a single file
  const handleExtract = useCallback(async (id: string, file: File): Promise<ReceiptData> => {
    updateReceipt(id, { status: 'extracting', error: null });

    try {
      const data = await ocrAPI.extract(file);
      updateReceipt(id, { receiptData: data, status: 'extracted' });
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'OCR 처리 실패';
      updateReceipt(id, { status: 'error', error: message });
      throw err;
    }
  }, [updateReceipt]);

  // Batch OCR Extract handler - Individual try-catch to allow partial success
  const handleBatchExtract = async () => {
    const pendingReceipts = receipts.filter(r => r.status === 'pending' || r.status === 'error');
    if (pendingReceipts.length === 0) return;

    setIsLoading(true);
    setError(null);

    let successCount = 0;
    for (const r of pendingReceipts) {
      try {
        if (r.file) {
          await handleExtract(r.id, r.file);
          successCount++;
        }
      } catch (err) {
        console.error(`Failed to extract receipt ${r.id}:`, err);
      }
    }

    if (successCount > 0) {
      setCurrentStep(2);
      setActiveTab(1);
      // Select the first successfully extracted receipt if none selected
      const firstSuccess = receipts.find(r => r.status === 'extracted');
      if (firstSuccess && !selectedReceiptId) {
        setSelectedReceiptId(firstSuccess.id);
      }
    }

    if (successCount < pendingReceipts.length) {
      setError(`${pendingReceipts.length - successCount}개의 영수증 처리에 실패했습니다.`);
    }

    setIsLoading(false);
  };

  // Audit Check handler
  const handleAudit = async (id: string, data: ReceiptData) => {
    updateReceipt(id, { status: 'auditing', error: null });

    try {
      const result = await auditAPI.check(data);
      updateReceipt(id, { auditResult: result, status: 'audited' });
    } catch (err) {
      const message = err instanceof Error ? err.message : '감사 실패';
      updateReceipt(id, { status: 'error', error: message });
      throw err;
    }
  };

  // Batch Audit Check handler - Individual try-catch to allow partial success
  const handleBatchAudit = async () => {
    const extractedReceipts = receipts.filter(r => (r.status === 'extracted' || r.status === 'error') && r.receiptData);
    if (extractedReceipts.length === 0) return;

    setIsLoading(true);
    setError(null);

    let successCount = 0;
    for (const r of extractedReceipts) {
      try {
        if (r.receiptData) {
          await handleAudit(r.id, r.receiptData);
          successCount++;
        }
      } catch (err) {
        console.error(`Failed to audit receipt ${r.id}:`, err);
      }
    }

    if (successCount > 0) {
      setCurrentStep(3);
      setActiveTab(2);
    }

    if (successCount < extractedReceipts.length) {
      setError(`${extractedReceipts.length - successCount}개의 감사 처리에 실패했습니다.`);
    }

    setIsLoading(false);
  };

  // PDF Confirm handler
  const handleConfirm = async (id: string) => {
    const receipt = receipts.find(r => r.id === id);
    if (!receipt || !receipt.receiptData || !receipt.auditResult) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await auditAPI.confirm(receipt.receiptData, receipt.auditResult);

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
        link.download = response.filename || `audit_report_${receipt.receiptData.receipt_id}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'PDF 생성 실패';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Batch PDF Confirm handler
  const handleBatchConfirm = async () => {
    const auditedReceipts = receipts.filter(r => r.status === 'audited' && r.receiptData && r.auditResult);
    if (auditedReceipts.length === 0) return;

    setIsLoading(true);
    setError(null);

    try {
      const batchPayload = auditedReceipts.map(r => ({
        receiptData: r.receiptData!,
        auditResult: r.auditResult!
      }));

      const response = await auditAPI.batchConfirm(batchPayload);

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
        link.download = response.filename || `batch_audit_report.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }
      // alert('모든 영수증 통합 PDF 보고서 다운로드 완료!');
    } catch (err) {
      const message = err instanceof Error ? err.message : '통합 PDF 생성 실패';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Quick demo scenario loader
  const loadScenario = (scenarioName: string) => {
    const data = MOCK_RECEIPTS[scenarioName];
    if (data) {
      const id = Math.random().toString(36).substring(2, 9);
      setReceipts(prev => [...prev, {
        id,
        receiptData: data,
        auditResult: null,
        status: 'extracted',
        error: null,
      }]);
      setSelectedReceiptId(id);
      setCurrentStep(2);
      setActiveTab(1);
    }
  };

  const selectedReceipt = receipts.find(r => r.id === selectedReceiptId) || (receipts.length > 0 ? receipts[0] : null);

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
                onClick={() => setIsRuleModalOpen(true)}
                onMouseDown={createRipple}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all relative overflow-hidden border border-gray-200 dark:border-slate-600 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700"
                aria-label="Toggle rules panel"
              >
                <BookOpen className="w-4 h-4" />
                현재 규칙
              </button>
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

      <RuleEditorModal isOpen={isRuleModalOpen} onClose={() => setIsRuleModalOpen(false)} />

      {error && (
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="bg-red-50 dark:bg-red-900/30 border-l-4 border-red-500 text-red-800 dark:text-red-300 px-6 py-4 rounded-lg shadow-sm animate-fadeIn">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <p className="font-semibold">처리 중 알림</p>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex max-w-[1600px] mx-auto">
        {/* Sidebar - Glass Morphism */}
        <aside className="w-72 glass p-6 shadow-lg min-h-screen border-r border-gray-200 dark:border-slate-700">
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
                  onClick={() => {
                    if (step <= currentStep) {
                      setActiveTab(step - 1);
                    }
                  }}
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

            {receipts.length > 0 && (activeTab === 1 || activeTab === 2) && (
              <div className="border-t border-gray-200 dark:border-slate-700 pt-6 mb-6">
                <h3 className="font-semibold mb-3 text-gray-700 dark:text-gray-300 flex items-center gap-2">
                  <Layers className="w-4 h-4" /> 영수증 목록 ({receipts.length})
                </h3>
                <div className="space-y-2 max-h-60 overflow-y-auto pr-2 custom-scrollbar">
                  {receipts.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setSelectedReceiptId(r.id)}
                      className={`w-full text-left text-xs px-3 py-2.5 rounded-lg border transition-all duration-200 flex items-center gap-2 ${
                        selectedReceiptId === r.id
                          ? 'bg-primary-100 border-primary-300 dark:bg-primary-900/40 dark:border-primary-700 text-primary-800 dark:text-primary-200'
                          : 'bg-white/50 border-gray-200 dark:bg-slate-800/50 dark:border-slate-700 text-gray-600 dark:text-gray-400 hover:border-primary-300'
                      }`}
                    >
                      <div className="w-8 h-8 rounded bg-gray-100 dark:bg-slate-700 flex-shrink-0 flex items-center justify-center overflow-hidden">
                        {r.preview ? (
                          <img src={r.preview} alt="" className="w-full h-full object-cover" />
                        ) : (
                          <FileText className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1 truncate">
                        <p className="font-medium truncate">{r.receiptData?.store_name || r.file?.name || '처리 전'}</p>
                        <p className="text-[10px] opacity-70">
                          {r.status === 'extracted' ? '데이터 확인 중' : r.status === 'audited' ? '감사 완료' : r.status === 'error' ? '오류 발생' : '대기 중'}
                        </p>
                      </div>
                      {selectedReceiptId === r.id && <ChevronRight className="w-3 h-3" />}
                    </button>
                  ))}
                </div>
              </div>
            )}

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
          <div className="max-w-[1400px] mx-auto">
            {/* Tabs */}
            <div className="flex gap-2 mb-8 glass rounded-xl p-2 shadow-sm">
              {tabData.map(({ label, icon: Icon }, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    if (idx < currentStep) setActiveTab(idx);
                  }}
                  onMouseDown={createRipple}
                  disabled={idx >= currentStep}
                  className={`flex-1 px-6 py-3 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 relative overflow-hidden ${
                    idx >= currentStep ? 'opacity-50 cursor-not-allowed' : ''
                  } ${
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
            {activeTab === 0 && (
              <UploadStep
                receipts={receipts}
                onFilesSelected={addReceipts}
                onRemoveReceipt={removeReceipt}
                onStartBatchExtract={handleBatchExtract}
                isProcessing={isLoading}
              />
            )}

            {activeTab === 1 && (
              <div className="animate-fadeIn">
                {selectedReceipt && selectedReceipt.receiptData ? (
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Left: Receipt Image Preview */}
                    <div className="lg:col-span-5 space-y-4">
                      <div className="sticky top-28">
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-bold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                            <ImageIcon className="w-5 h-5 text-primary-500" /> 영수증 원본
                          </h3>
                        </div>
                        <div className="card overflow-hidden bg-slate-100 dark:bg-slate-800 border-2 border-primary-100 dark:border-primary-900/30 shadow-soft">
                          {selectedReceipt.preview ? (
                            <img
                              src={selectedReceipt.preview}
                              alt="Selected Receipt"
                              className="w-full h-auto max-h-[70vh] object-contain mx-auto"
                            />
                          ) : (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                              <ImageIcon className="w-12 h-12 mb-2 opacity-20" />
                              <p>이미지 미리보기를 사용할 수 없습니다</p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Right: Data Editor */}
                    <div className="lg:col-span-7 space-y-6">
                      <div className="flex justify-between items-center bg-white/50 dark:bg-slate-800/50 p-4 rounded-xl border border-primary-100 dark:border-primary-900/30">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <span className="font-bold text-primary-600">선택됨:</span>
                          <span className="font-medium text-gray-800 dark:text-gray-200">{selectedReceipt.receiptData.store_name}</span>
                        </div>
                        <div className="text-xs font-bold bg-primary-100 text-primary-700 px-3 py-1 rounded-full">
                          {receipts.indexOf(selectedReceipt) + 1} / {receipts.length}
                        </div>
                      </div>

                      <DataEditor
                        data={selectedReceipt.receiptData}
                        onChange={(newData) => updateReceipt(selectedReceipt.id, { receiptData: newData })}
                      />

                      <div className="flex gap-4 justify-center mt-8">
                        <button
                          onClick={handleBatchAudit}
                          onMouseDown={createRipple}
                          disabled={isLoading || receipts.every(r => r.status === 'audited')}
                          className="btn-success px-10 py-4 text-lg flex items-center gap-2 w-full lg:w-auto justify-center"
                        >
                          {isLoading ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> AI 감사 중...</>
                          ) : (
                            <><Rocket className="w-5 h-5" /> 모든 영수증 AI 감사 실행</>
                          )}
                        </button>
                      </div>

                      {selectedReceipt.auditResult && (
                        <div className="mt-8 animate-fadeIn">
                          <AuditResults result={selectedReceipt.auditResult} />
                          <div className="text-center mt-6">
                            <button
                              onClick={() => setActiveTab(2)}
                              onMouseDown={createRipple}
                              className="btn-primary px-8 py-3 flex items-center gap-2 mx-auto"
                            >
                              최종 결과 확인 <ArrowRight className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-20 card bg-white/50 dark:bg-slate-800/50">
                    <Upload className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-gray-700 dark:text-gray-300">추출된 데이터가 없습니다</h3>
                    <p className="text-gray-500 dark:text-gray-400 mt-2">먼저 영수증을 업로드하고 데이터 추출을 완료해주세요</p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 2 && (
              <div className="animate-fadeIn">
                {selectedReceipt && selectedReceipt.auditResult ? (
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Left: Image Preview */}
                    <div className="lg:col-span-4">
                      <div className="sticky top-28">
                        <div className="card overflow-hidden bg-slate-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700">
                          <img
                            src={selectedReceipt.preview}
                            alt="Receipt"
                            className="w-full h-auto object-contain"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Right: Results */}
                    <div className="lg:col-span-8 space-y-8">
                      <div className="flex justify-between items-center bg-white/50 dark:bg-slate-800/50 p-4 rounded-xl border border-primary-100 dark:border-primary-900/30">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <span className="font-bold text-primary-600">선택된 영수증 감사 결과</span>
                        </div>
                      </div>

                      <AuditResults result={selectedReceipt.auditResult} compact />

                      <div className="border-t border-gray-200 dark:border-slate-700 pt-8"></div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <button
                          onClick={() => handleConfirm(selectedReceipt.id)}
                          onMouseDown={createRipple}
                          disabled={isLoading}
                          className="btn-primary px-6 py-4 flex items-center justify-center gap-2"
                        >
                          {isLoading ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> 생성 중...</>
                          ) : (
                            <><FileDown className="w-5 h-5" /> 현재 영수증 PDF 다운로드</>
                          )}
                        </button>

                        <button
                          onClick={handleBatchConfirm}
                          onMouseDown={createRipple}
                          disabled={isLoading}
                          className="btn-success px-6 py-4 flex items-center justify-center gap-2"
                        >
                          {isLoading ? (
                            <><Loader2 className="w-5 h-5 animate-spin" /> 일괄 처리 중...</>
                          ) : (
                            <><Layers className="w-5 h-5" /> 모든 영수증 PDF 일괄 다운로드</>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-20 card bg-white/50 dark:bg-slate-800/50">
                    <Search className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-gray-700 dark:text-gray-300">감사 결과가 없습니다</h3>
                    <p className="text-gray-500 dark:text-gray-400 mt-2">편집 탭에서 AI 감사를 먼저 실행해주세요</p>
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
