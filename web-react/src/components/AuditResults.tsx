/**
 * Audit Results Component
 * Equivalent to web/src/components/audit_result_component.py
 */

import {
  CheckCircle, XCircle, AlertTriangle, ClipboardList,
  ShieldAlert, ShieldCheck, Lightbulb, BookOpen,
} from 'lucide-react';
import { useCountUp } from '@/hooks/useCountUp';
import type { AuditResult } from '@/types';

interface AuditResultsProps {
  result: AuditResult;
  compact?: boolean;
}

export const AuditResults: React.FC<AuditResultsProps> = ({ result, compact = false }) => {
  const { audit_decision, violation_score, violations, reasoning } = result;

  const animatedScore = useCountUp(violation_score * 100, 1200);

  const decisionColors = {
    Pass: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-500',
      text: 'text-green-700 dark:text-green-400',
      gradient: 'from-green-500 to-green-600',
      Icon: CheckCircle,
    },
    'Anomaly Detected': {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-500',
      text: 'text-red-700 dark:text-red-400',
      gradient: 'from-red-500 to-red-600',
      Icon: XCircle,
    },
    Warning: {
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
      border: 'border-yellow-500',
      text: 'text-yellow-700 dark:text-yellow-400',
      gradient: 'from-yellow-500 to-yellow-600',
      Icon: AlertTriangle,
    },
  };

  const colors = decisionColors[audit_decision] || decisionColors.Warning;
  const DecisionIcon = colors.Icon;

  if (compact) {
    return (
      <div className={`card p-5 border-l-4 ${colors.border}`}>
        <div className="flex justify-between items-center">
          <div>
            <h3 className={`font-bold text-lg ${colors.text} flex items-center gap-2`}>
              <DecisionIcon className="w-6 h-6" />
              {audit_decision}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              위반 가능성: {animatedScore.toFixed(1)}%
            </p>
          </div>
        </div>
        {violations.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-red-500" />
              {violations.length}개의 위반 항목 발견
            </p>
            <ul className="text-sm space-y-1 text-gray-600 dark:text-gray-400">
              {violations.map((v, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-red-500 mt-0.5">•</span>
                  <span>{v.reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto animate-fadeIn">
      <div className="mb-6">
        <h2 className="text-3xl font-bold mb-2">
          <span className="text-gradient">AI 감사 결과</span>
        </h2>
        <p className="text-gray-600 dark:text-gray-400">자동 감사 시스템이 영수증을 분석한 결과입니다</p>
      </div>

      {/* Decision Banner */}
      <div className={`card-hover p-8 mb-6 border-l-4 ${colors.border}`}>
        <div className="flex items-center justify-center gap-4">
          <div className={`w-16 h-16 rounded-full bg-gradient-to-br ${colors.gradient} flex items-center justify-center shadow-lg`}>
            <DecisionIcon className="w-8 h-8 text-white" />
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">감사 결과</p>
            <h3 className={`text-3xl font-bold ${colors.text}`}>
              {audit_decision}
            </h3>
          </div>
        </div>
      </div>

      {/* Violation Score with Count-up */}
      <div className="card-hover p-6 mb-6">
        <h4 className="font-semibold text-lg mb-4 text-gray-800 dark:text-gray-200 text-center">위반 가능성 점수</h4>
        <div className="max-w-md mx-auto">
          <div className="relative w-full bg-gray-200 dark:bg-slate-600 rounded-full h-6 mb-3 overflow-hidden">
            <div
              className={`h-6 rounded-full no-color-transition transition-[width] duration-1000 ease-out ${
                violation_score > 0.7
                  ? 'bg-gradient-to-r from-red-500 to-red-600'
                  : violation_score > 0.3
                  ? 'bg-gradient-to-r from-yellow-500 to-yellow-600'
                  : 'bg-gradient-to-r from-green-500 to-green-600'
              }`}
              style={{ width: `${animatedScore}%` }}
            ></div>
          </div>
          <p className="text-center text-3xl font-bold text-gray-900 dark:text-gray-100">
            {animatedScore.toFixed(1)}%
          </p>
          <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-1">
            {violation_score > 0.7 ? '높은 위반 가능성' : violation_score > 0.3 ? '중간 위반 가능성' : '낮은 위반 가능성'}
          </p>
        </div>
      </div>

      {/* Reasoning */}
      {reasoning && (
        <div className="card-hover p-6 mb-6">
          <h4 className="font-semibold text-lg mb-3 text-gray-800 dark:text-gray-200 flex items-center gap-2">
            <ClipboardList className="w-5 h-5 text-primary-500" /> 판단 근거
          </h4>
          <div className={`p-4 rounded-lg ${colors.bg} border ${colors.border}`}>
            <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{reasoning}</p>
          </div>
        </div>
      )}

      {/* Violations */}
      {violations.length > 0 ? (
        <div className="card-hover p-6 mb-6">
          <h4 className="font-semibold text-lg mb-4 text-gray-800 dark:text-gray-200 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-500" /> 위반 항목 상세
          </h4>
          <div className="space-y-4">
            {violations.map((violation, idx) => (
              <div key={idx} className="border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20 rounded-r-lg p-4 hover:shadow-md hover:scale-[1.005] transition-all">
                <div className="flex justify-between items-start mb-3">
                  <h5 className="font-semibold text-red-900 dark:text-red-300 text-lg">
                    위반 항목 #{idx + 1}
                  </h5>
                  <div className="flex flex-col items-end gap-1">
                    <span className="text-xs bg-red-600 text-white px-3 py-1 rounded-full font-semibold">HIGH</span>
                    <span className="text-xs text-gray-600 dark:text-gray-400">품목 ID: {violation.item_id}</span>
                  </div>
                </div>
                <div className="mb-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium">사유</p>
                  <p className="text-gray-800 dark:text-gray-200">{violation.reason}</p>
                </div>
                <div className="bg-white dark:bg-slate-700 p-3 rounded-lg border border-red-200 dark:border-red-800">
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-medium flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" /> 관련 규정
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300">{violation.policy_reference}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="card-hover p-8 mb-6 border-l-4 border-green-500">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center shadow-lg">
              <ShieldCheck className="w-8 h-8 text-white" />
            </div>
            <p className="text-2xl font-semibold text-green-800 dark:text-green-400">위반 항목이 발견되지 않았습니다!</p>
            <p className="text-gray-600 dark:text-gray-400 mt-2">모든 항목이 회계 규정을 준수합니다</p>
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="card p-6 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800">
        <div className="flex items-start gap-3">
          <Lightbulb className="w-6 h-6 text-primary-500 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <h4 className="font-semibold text-lg mb-3 text-primary-900 dark:text-primary-300">권장 사항</h4>
            {violations.length === 0 ? (
              <p className="text-primary-800 dark:text-primary-300/80">영수증이 회계 규정을 준수합니다. 최종 확정을 진행해주세요.</p>
            ) : (
              <ul className="space-y-2 text-primary-800 dark:text-primary-300/80">
                <li className="flex items-start gap-2">
                  <span className="text-primary-600 dark:text-primary-400 mt-1">•</span>
                  <span>위반 항목을 확인하고 데이터를 수정하세요</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary-600 dark:text-primary-400 mt-1">•</span>
                  <span>잘못 인식된 경우 데이터 편집 탭에서 수정 후 재감사하세요</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary-600 dark:text-primary-400 mt-1">•</span>
                  <span>위반 항목이 있는 영수증 확정 시 추후 문제가 될 수 있습니다</span>
                </li>
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
