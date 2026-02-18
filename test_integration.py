import os
import json
import time

# 우리가 만든 모듈들 불러오기
from core.rag_engine.ingest import run_ingestion
from core.audit_agent.reasoning import AuditReasoning

def run_test():
    print("🚀 [1단계] 지식 베이스 구축 (Real-time Ingestion)")
    pdf_path = "data/raw/organization_policy.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ 오류: '{pdf_path}' 파일이 없습니다. 규정 PDF를 먼저 만들어주세요!")
        return

    # 1. ingest.py의 함수를 호출해서 DB에 저장
    success = run_ingestion(pdf_path)
    if not success:
        return

    print("\n🤖 [2단계] AI 감사관 초기화 (Agent Loading)")
    try:
        agent = AuditReasoning()
        print("   -> 에이전트 로딩 완료!")
    except Exception as e:
        print(f"❌ 에이전트 로딩 실패: {e}")
        return

    # --- 테스트 케이스 정의 ---
    test_cases = [
        {
            "name": "CASE 1: 오타 공격 (참미술)",
            "receipt": {
                "receipt_id": "TEST-001",
                "store_name": "청춘포차 연세대점",
                "items": [
                    {"id": 1, "name": "카쓰", "unit_price": 4500, "count": 2, "price": 9000},
                    {"id": 2, "name": "오뎅탕", "unit_price": 12000, "count": 1, "price": 12000}
                ]
            },
            "expected": "Anomaly Detected" # 위반 나와야 함
        },
        {
            "name": "CASE 2: 정상 구매 (붓, 물감)",
            "receipt": {
                "receipt_id": "TEST-002",
                "store_name": "알파문구",
                "items": [
                    {"id": 1, "name": "처음처럼", "unit_price": 3000, "count": 1, "price": 3000}
                ]
            },
            "expected": "Pass" # 통과 나와야 함
        }
    ]

    print("\n🔍 [3단계] 감사 수행 및 리랭킹 검증")
    
    for case in test_cases:
        print(f"\n>>> 실행 중: {case['name']}")
        
        # reasoning.py의 analyze 함수 호출 (규정을 안 넘겨서 스스로 리랭킹하게 만듦!)
        # agent_llm=self.llm 로직이 내부에서 돌아감
        result = agent.analyze(case['receipt'])
        
        print(f"   [결과] 판정: {result.get('audit_decision')} | 점수: {result.get('violation_score')}")
        print(f"   [근거] {result.get('reasoning')}")
        
        # 검증
        if result.get('audit_decision') == case['expected']:
            print("   ✅ 테스트 통과!")
        else:
            print(f"   ❌ 테스트 실패 (기대값: {case['expected']})")

if __name__ == "__main__":
    run_test()