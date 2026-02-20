/**
 * Upload Step Component
 * Equivalent to web/src/components/upload_component.py
 */

import { useState, useRef } from 'react';
import { Camera, FolderOpen, X, CheckCircle, Lightbulb, Loader2, Trash2, FileText, Play, FileUp, MessageSquarePlus, Send } from 'lucide-react';
import type { ReceiptItemState } from '@/types';
import { auditAPI } from '@/services/api';

interface UploadStepProps {
  receipts: ReceiptItemState[];
  onFilesSelected: (files: File[]) => void;
  onRemoveReceipt: (id: string) => void;
  onStartBatchExtract: () => void;
  isProcessing: boolean;
}

export const UploadStep: React.FC<UploadStepProps> = ({ 
  receipts, 
  onFilesSelected, 
  onRemoveReceipt, 
  onStartBatchExtract,
  isProcessing 
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [rulesFile, setRulesFile] = useState<File | null>(null);
  const [rulesText, setRulesText] = useState('');
  const [isUploadingRules, setIsUploadingRules] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const rulesInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp'];
  const RULES_FORMATS = ['.pdf', '.txt', '.docx', '.doc'];

  const handleFileChange = (files: FileList | null) => {
    if (!files) return;
    
    const validFiles: File[] = [];
    Array.from(files).forEach(file => {
      if (file.size > MAX_FILE_SIZE) {
        alert(`${file.name}: 파일 크기가 너무 큽니다. (최대: 10MB)`);
        return;
      }
      if (!SUPPORTED_FORMATS.includes(file.type)) {
        alert(`${file.name}: 지원하지 않는 파일 형식입니다.`);
        return;
      }
      validFiles.push(file);
    });

    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  };

  const handleRulesUpload = async () => {
    if (!rulesFile && !rulesText.trim()) {
      alert('업로드할 파일이나 텍스트를 입력해주세요.');
      return;
    }

    setIsUploadingRules(true);
    try {
      const result = await auditAPI.uploadRules(rulesFile || undefined, rulesText || undefined);
      alert('조직 내부 규정이 성공적으로 반영되었습니다!');
      setRulesFile(null);
      setRulesText('');
      if (rulesInputRef.current) rulesInputRef.current.value = '';
    } catch (error) {
      alert(`규정 업로드 실패: ${error}`);
    } finally {
      setIsUploadingRules(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileChange(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileChange(e.dataTransfer.files);
  };

  return (
    <div className="max-w-6xl mx-auto animate-fadeIn space-y-8">
      {/* 1. Organizational Rules Upload Section */}
      <div className="card-hover p-8 border-2 border-primary-100 dark:border-primary-900/30 bg-primary-50/30 dark:bg-primary-900/10">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 bg-primary-500 rounded-xl flex items-center justify-center shadow-lg">
            <FileUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-100">조직 내부 감사 규정 등록</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">PDF, TXT, Word 파일 또는 직접 텍스트를 입력하여 AI 감사 기준을 설정하세요</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">파일 업로드 (PDF, TXT, DOCX)</label>
            <div 
              onClick={() => rulesInputRef.current?.click()}
              className="border-2 border-dashed border-primary-200 dark:border-primary-800 rounded-xl p-6 text-center cursor-pointer hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-all"
            >
              <input
                ref={rulesInputRef}
                type="file"
                accept=".pdf,.txt,.docx,.doc"
                className="hidden"
                onChange={(e) => setRulesFile(e.target.files?.[0] || null)}
              />
              {rulesFile ? (
                <div className="flex items-center justify-center gap-2 text-primary-600 dark:text-primary-400 font-medium">
                  <FileText className="w-5 h-5" />
                  {rulesFile.name}
                </div>
              ) : (
                <div className="text-gray-500">
                  <FolderOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  규정 파일 선택
                </div>
              )}
            </div>
          </div>

          <div className="space-y-4">
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">직접 텍스트 입력</label>
            <div className="relative">
              <textarea
                value={rulesText}
                onChange={(e) => setRulesText(e.target.value)}
                placeholder="감사 시 참고할 내부 규정이나 지침을 입력하세요..."
                className="w-full h-[115px] p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all resize-none text-sm"
              />
              <MessageSquarePlus className="absolute bottom-4 right-4 w-5 h-5 text-gray-300 pointer-events-none" />
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            onClick={handleRulesUpload}
            disabled={isUploadingRules || (!rulesFile && !rulesText.trim())}
            className="btn-primary px-8 py-3 flex items-center gap-2"
          >
            {isUploadingRules ? (
              <><Loader2 className="w-5 h-5 animate-spin" /> 규정 반영 중...</>
            ) : (
              <><Send className="w-5 h-5" /> 규정 데이터베이스 반영</>
            )}
          </button>
        </div>
      </div>

      {/* 2. Receipt Upload Section */}
      <div>
        <div className="mb-6">
          <h2 className="text-3xl font-bold mb-2">
            <span className="text-gradient">영수증 이미지 업로드</span>
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            지원 형식: <span className="font-medium">JPG, PNG, BMP, WEBP</span> (최대 10MB)
          </p>
        </div>

        <div className="card-hover p-8 mb-8">
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-all duration-200 ${
              isDragOver
                ? 'border-primary-400 bg-primary-50 dark:bg-primary-900/20 scale-[1.01]'
                : 'border-gray-300 dark:border-slate-600 hover:border-primary-400'
            }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".jpg,.jpeg,.png,.bmp,.webp"
              onChange={handleFileSelect}
              className="hidden"
              multiple
            />

            <div>
              <div className="w-20 h-20 bg-primary-50 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Camera className="w-9 h-9 text-primary-500" />
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-2 text-lg">영수증 이미지를 선택하세요 (여러 장 가능)</p>
              <p className="text-gray-400 dark:text-gray-500 text-sm mb-6">또는 이 영역에 파일을 드래그하세요</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn-primary px-8 py-3 text-lg inline-flex items-center gap-2"
              >
                <FolderOpen className="w-5 h-5" /> 파일 선택
              </button>
            </div>
          </div>
        </div>

        {receipts.length > 0 && (
          <div className="space-y-6 animate-fadeIn">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-800 dark:text-gray-200">
                업로드된 영수증 ({receipts.length})
              </h3>
              <button
                onClick={onStartBatchExtract}
                disabled={isProcessing || receipts.every(r => r.status !== 'pending' && r.status !== 'error')}
                className="btn-success px-8 py-3 inline-flex items-center gap-2"
              >
                {isProcessing ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /> 처리 중...</>
                ) : (
                  <><Play className="w-5 h-5" /> 모든 영수증 데이터 추출 시작</>
                )}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {receipts.map((receipt) => (
                <div key={receipt.id} className="card p-4 flex gap-4 items-center relative group">
                  <div className="w-20 h-24 bg-gray-100 dark:bg-slate-700 rounded-lg overflow-hidden flex-shrink-0 border border-gray-200 dark:border-slate-600">
                    {receipt.preview ? (
                      <img src={receipt.preview} alt="Preview" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <FileText className="w-8 h-8 text-gray-400" />
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-800 dark:text-gray-200 truncate pr-8">
                      {receipt.file?.name || 'Scenario Data'}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                      {receipt.file ? `${(receipt.file.size / 1024).toFixed(1)} KB` : 'Mock Data'}
                    </p>
                    
                    <div className="flex items-center gap-2">
                      {receipt.status === 'pending' && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">대기 중</span>
                      )}
                      {receipt.status === 'extracting' && (
                        <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded flex items-center gap-1">
                          <Loader2 className="w-3 h-3 animate-spin" /> 추출 중
                        </span>
                      )}
                      {receipt.status === 'extracted' && (
                        <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> 완료
                        </span>
                      )}
                      {receipt.status === 'error' && (
                        <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded" title={receipt.error || ''}>오류</span>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => onRemoveReceipt(receipt.id)}
                    className="absolute top-4 right-4 text-gray-400 hover:text-red-500 transition-colors p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="mt-8 p-6 card bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
        <p className="font-semibold mb-3 text-primary-900 dark:text-primary-300 flex items-center gap-2">
          <Lightbulb className="w-5 h-5" /> 감사 팁
        </p>
        <ul className="text-sm text-primary-800 dark:text-primary-300/80 space-y-2">
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>상단에 조직 내부 규정을 먼저 등록하면, AI가 해당 규정을 기준으로 영수증을 감사하게 됩니다.</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>영수증 여러 장을 한꺼번에 선택하여 동시에 처리할 수 있습니다.</span>
          </li>
        </ul>
      </div>
    </div>
  );
};
