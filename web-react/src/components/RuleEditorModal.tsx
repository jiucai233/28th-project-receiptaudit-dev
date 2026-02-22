import { useState, useEffect } from 'react';
import { X, ShieldAlert, Loader2, Database, Trash2, Edit2, Check, XCircle } from 'lucide-react';
import { auditAPI } from '@/services/api';
import type { RulesResponse, RulesEntry } from '@/types';

interface RuleEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RuleEditorModal = ({ isOpen, onClose }: RuleEditorModalProps) => {
  const [rulesData, setRulesData] = useState<RulesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const fetchRules = async () => {
    setIsLoading(true);
    try {
      const data = await auditAPI.getRules();
      setRulesData(data);
      setError(null);
    } catch (err) {
      setError('규칙을 불러오는 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchRules();
      setEditingId(null);
    }
  }, [isOpen]);

  const handleDelete = async (id: string) => {
    if (!confirm('정말 이 규칙을 삭제하시겠습니까?')) return;
    
    setIsLoading(true);
    try {
      await auditAPI.deleteRule(id);
      await fetchRules();
    } catch (err) {
      alert('규칙 삭제 실패');
      setIsLoading(false);
    }
  };

  const startEdit = (rule: RulesEntry) => {
    if (!rule.id) {
       alert('수정할 수 없는 기본 규칙입니다.');
       return;
    }
    setEditingId(rule.id);
    setEditContent(rule.content);
  };

  const handleSave = async (id: string) => {
    setIsLoading(true);
    try {
      await auditAPI.updateRule(id, editContent);
      setEditingId(null);
      await fetchRules();
    } catch (err) {
      alert('규칙 수정 실패');
      setIsLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/60 backdrop-blur-sm animate-fadeIn p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[85vh] flex flex-col overflow-hidden border border-gray-200 dark:border-slate-800 animate-slideUp">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-slate-800 bg-gray-50/80 dark:bg-slate-800/80">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 flex items-center justify-center bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl shadow-md">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">조직 내부 감사 규칙 관리</h2>
              {rulesData && (
                <div className="flex items-center mt-1 gap-2">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    rulesData.mode === 'rag' 
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' 
                      : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400'
                  }`}>
                    {rulesData.mode === 'rag' ? 'RAG DB 연동됨' : '기본 모드'}
                  </span>
                  {rulesData.mode === 'rag' && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">총 {rulesData.total_chunks}개 조항 적용 중</span>
                  )}
                </div>
              )}
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2.5 text-gray-400 hover:text-gray-600 hover:bg-gray-200 dark:hover:bg-slate-700 rounded-xl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-50 dark:bg-slate-950 custom-scrollbar relative">
          {isLoading && !rulesData ? (
            <div className="flex flex-col items-center justify-center py-32 text-gray-500">
              <Loader2 className="w-10 h-10 animate-spin mb-4 text-primary-500" />
              <p className="text-lg">데이터베이스에서 규칙을 불러오는 중...</p>
            </div>
          ) : error ? (
            <div className="text-center py-20 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-100 dark:border-red-900/30 text-red-600 dark:text-red-400">
              <ShieldAlert className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg mb-4">{error}</p>
              <button onClick={fetchRules} className="px-6 py-2.5 bg-white dark:bg-slate-800 text-red-600 dark:text-red-400 shadow-sm rounded-lg hover:bg-gray-50 transition-colors font-medium">재시도</button>
            </div>
          ) : rulesData && rulesData.rules.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 relative">
              {isLoading && rulesData && (
                <div className="absolute inset-0 bg-white/40 dark:bg-slate-900/40 backdrop-blur-[2px] z-10 flex items-center justify-center rounded-xl">
                  <div className="bg-white dark:bg-slate-800 px-6 py-3 rounded-full shadow-lg flex items-center gap-3 border border-gray-100 dark:border-slate-700">
                    <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
                    <span className="font-medium text-gray-700 dark:text-gray-300">처리 중...</span>
                  </div>
                </div>
              )}
              {rulesData.rules.map((rule, idx) => {
                const isEditing = editingId === rule.id;
                const isFallback = rulesData.mode === 'fallback';
                
                return (
                  <div 
                    key={rule.id || idx} 
                    className={`group bg-white dark:bg-slate-900 rounded-xl p-6 border shadow-sm transition-all duration-200 
                      ${isEditing ? 'border-primary-400 ring-4 ring-primary-50 dark:ring-primary-900/30' : 'border-gray-200 dark:border-slate-800 hover:border-primary-300 hover:shadow-md'}`}
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-2.5">
                        <div className="p-1.5 bg-primary-50 dark:bg-primary-900/30 rounded-lg text-primary-500">
                          <Database className="w-4 h-4 flex-shrink-0" />
                        </div>
                        <h3 className="font-bold text-gray-800 dark:text-gray-200 text-[15px]">{rule.title}</h3>
                      </div>
                      
                      {!isFallback && rule.id && (
                        <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{ opacity: isEditing ? 1 : undefined }}>
                          {isEditing ? (
                            <>
                              <button 
                                onClick={() => handleSave(rule.id!)}
                                disabled={isLoading || !editContent.trim() || editContent === rule.content}
                                className="px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 disabled:opacity-50"
                              >
                                {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} 저장
                              </button>
                              <button 
                                onClick={handleCancelEdit}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-gray-100 dark:bg-slate-800 hover:bg-gray-200 dark:hover:bg-slate-700 text-gray-700 dark:text-gray-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
                              >
                                <XCircle className="w-3.5 h-3.5" /> 취소
                              </button>
                            </>
                          ) : (
                            <>
                              <button 
                                onClick={() => startEdit(rule)}
                                className="p-2 text-blue-600 bg-blue-50 hover:bg-blue-100 dark:text-blue-400 dark:bg-blue-900/20 dark:hover:bg-blue-900/40 rounded-lg transition-colors"
                                title="규칙 수정"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handleDelete(rule.id!)}
                                className="p-2 text-red-600 bg-red-50 hover:bg-red-100 dark:text-red-400 dark:bg-red-900/20 dark:hover:bg-red-900/40 rounded-lg transition-colors"
                                title="규칙 삭제"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>

                    {isEditing ? (
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full min-h-[140px] p-4 text-sm text-gray-800 dark:text-gray-100 bg-slate-50 dark:bg-slate-800/50 border border-primary-200 dark:border-primary-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none leading-relaxed"
                        placeholder="이 항목을 감사할 때 고려해야 할 핵심 규칙을 상세히 평가해주세요..."
                        autoFocus
                      />
                    ) : (
                      <p className="text-[14px] text-gray-600 dark:text-gray-400 leading-relaxed whitespace-pre-wrap pl-1">
                        {rule.content}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-24 text-gray-500 bg-white dark:bg-slate-900 rounded-xl border border-dashed border-gray-300 dark:border-slate-700">
              <div className="w-16 h-16 bg-gray-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-5">
                <Database className="w-8 h-8 text-gray-400" />
              </div>
              <p className="text-xl font-bold text-gray-700 dark:text-gray-300 mb-2">활성화된 규칙이 없습니다</p>
              <p className="text-[15px] text-gray-500 max-w-sm text-center">AI 감사를 위한 기준 규정을 업로드 탭에서 먼저 등록해주세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
