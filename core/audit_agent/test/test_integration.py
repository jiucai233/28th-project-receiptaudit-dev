import os
import json
import time
from dotenv import load_dotenv

# 우리가 만든 모듈들 불러오기
from core.rag_engine.ingest import run_ingestion
from core.audit_agent.reasoning import AuditReasoning

def run_test():
    # 환경변수 로드 (.env 파일에서 네이버 API 키를 가져오기 위함)
    load_dotenv()

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

    # --- 테스트 케이스 정의 (store_address 추가!) ---
    test_cases = [
        {
            "name": "CASE 1: 규정 위반",
            "receipt": {
                "receipt_id": "TEST-001",
                "store_name": "참숯닭갈비구이",
                "store_address": "부산 동래구 안락로 27 (안락동) 1층", # [NEW] 주소 추가
                "items": [
                    {"id": 1, "name": "숯불소금구이", "unit_price": 10000, "count": 1, "price": 10000},
                    {"id": 2, "name": "참미술", "unit_price": 4500, "count": 3, "price": 13500},
                    {"id": 3, "name": "햇반", "unit_price": 2000, "count": 3, "price": 6000}
                ]
            },
            "expected": "Anomaly Detected" # 위반 나와야 함
        },
        {
            "name": "CASE 2: 정상 구매",
            "receipt": {
                "receipt_id": "TEST-002",
                "store_name": "롯데리아 상암점",
                "store_address": "마포구 상암동 1601번지 KGIT센터 1층 150호", # [NEW] 주소 추가
                "items": [
                    {"id": 1, "name": "치킨버거", "unit_price": 5000, "count": 1, "price": 5000}
                ]
            },
            "expected": "Pass" # 통과 나와야 함
        },
        {
            "name": "CASE 3: 정상 구매",
            "receipt": {
                "receipt_id": "TEST-002",
                "store_name": "청년다방(선릉역점)",
                "store_address": "서울특별시 강남구 선릉로86길 31 1층", # [NEW] 주소 추가
                "items": [
                    {"id": 1, "name": "불향차돌떡볶이", "unit_price": 17500, "count": 1, "price": 17500},
                    {"id": 2, "name": "찰순대", "unit_price": 4000, "count": 1, "price": 4000},
                    {"id": 3, "name": "쫄면사리", "unit_price": 2000, "count": 1, "price": 2000},
                    {"id": 4, "name": "콜라", "unit_price": 2000, "count": 1, "price": 2000}
                ]
            },
            "expected": "Pass" # 통과 나와야 함
        }
    ]

    print("\n🔍 [3단계] 감사 수행 및 리랭킹 검증")
    
    for case in test_cases:
        print(f"\n>>> 실행 중: {case['name']}")
        
        # reasoning.py의 analyze 함수 호출
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