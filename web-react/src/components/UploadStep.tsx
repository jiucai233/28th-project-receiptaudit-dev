/**
 * Upload Step Component
 * Equivalent to web/src/components/upload_component.py
 */

import { useState, useRef } from 'react';
import { Camera, FolderOpen, X, CheckCircle, Lightbulb, Loader2, Trash2, FileText, Play } from 'lucide-react';
import type { ReceiptItemState } from '@/types';

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
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp'];

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
    <div className="max-w-4xl mx-auto animate-fadeIn">
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

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

      <div className="mt-8 p-6 card bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
        <p className="font-semibold mb-3 text-primary-900 dark:text-primary-300 flex items-center gap-2">
          <Lightbulb className="w-5 h-5" /> 업로드 팁
        </p>
        <ul className="text-sm text-primary-800 dark:text-primary-300/80 space-y-2">
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>영수증 여러 장을 한꺼번에 선택하여 동시에 처리할 수 있습니다</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>이미지가 선명할수록 OCR 인식 정확도가 높아집니다</span>
          </li>
        </ul>
      </div>
    </div>
  );
};
