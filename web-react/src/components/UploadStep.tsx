/**
 * Upload Step Component
 * Equivalent to web/src/components/upload_component.py
 */

import { useState, useRef } from 'react';
import { Camera, FolderOpen, X, CheckCircle, Lightbulb, Loader2 } from 'lucide-react';
import type { ReceiptData } from '@/types';

interface UploadStepProps {
  onUploadSuccess: (data: ReceiptData) => void;
  onExtract: (file: File) => Promise<ReceiptData>;
}

export const UploadStep: React.FC<UploadStepProps> = ({ onUploadSuccess, onExtract }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/bmp', 'image/webp'];

  const processFile = (file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      alert(`파일 크기가 너무 큽니다. (최대: 10MB, 현재: ${(file.size / 1024 / 1024).toFixed(2)}MB)`);
      return;
    }
    if (!SUPPORTED_FORMATS.includes(file.type)) {
      alert('지원하지 않는 파일 형식입니다. (JPG, PNG, BMP, WEBP만 가능)');
      return;
    }

    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleExtract = async () => {
    if (!selectedFile) return;

    setIsExtracting(true);
    try {
      const data = await onExtract(selectedFile);
      onUploadSuccess(data);
    } catch (error) {
      alert(`OCR 처리 중 오류: ${error}`);
    } finally {
      setIsExtracting(false);
    }
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

      <div className="card-hover p-8">
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
          />

          {!selectedFile ? (
            <div>
              <div className="w-20 h-20 bg-primary-50 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
                <Camera className="w-9 h-9 text-primary-500" />
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-2 text-lg">영수증 이미지를 선택하세요</p>
              <p className="text-gray-400 dark:text-gray-500 text-sm mb-6">또는 이 영역에 파일을 드래그하세요</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="btn-primary px-8 py-3 text-lg inline-flex items-center gap-2"
              >
                <FolderOpen className="w-5 h-5" /> 파일 선택
              </button>
            </div>
          ) : (
            <div className="space-y-6">
              {preview && (
                <div className="max-w-md mx-auto">
                  <img src={preview} alt="Receipt preview" className="rounded-xl shadow-soft border border-gray-200 dark:border-slate-600" />
                </div>
              )}

              <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 p-5 rounded-xl inline-block">
                <p className="font-semibold text-gray-800 dark:text-gray-200">{selectedFile.name}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  파일 크기: <span className="font-medium">{(selectedFile.size / 1024).toFixed(2)} KB</span>
                </p>
              </div>

              <div className="flex gap-3 justify-center">
                <button
                  onClick={handleExtract}
                  disabled={isExtracting}
                  className="btn-success px-8 py-3 inline-flex items-center gap-2"
                >
                  {isExtracting ? (
                    <><Loader2 className="w-5 h-5 animate-spin" /> OCR 처리 중...</>
                  ) : (
                    <><CheckCircle className="w-5 h-5" /> OCR 시작</>
                  )}
                </button>
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    setPreview(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="btn-secondary px-6 py-3 inline-flex items-center gap-2"
                >
                  <X className="w-4 h-4" /> 취소
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 p-6 card bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
        <p className="font-semibold mb-3 text-primary-900 dark:text-primary-300 flex items-center gap-2">
          <Lightbulb className="w-5 h-5" /> 업로드 팁
        </p>
        <ul className="text-sm text-primary-800 dark:text-primary-300/80 space-y-2">
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>영수증이 잘 보이도록 촬영해주세요</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>조명이 밝은 곳에서 찍으면 인식률이 높아집니다</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
            <span>영수증이 구겨지지 않도록 펼쳐서 촬영하세요</span>
          </li>
        </ul>
      </div>
    </div>
  );
};
