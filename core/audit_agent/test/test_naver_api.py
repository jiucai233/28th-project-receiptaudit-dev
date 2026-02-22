import os
import json
from dotenv import load_dotenv

# 우리가 만든 네이버 검증기 모듈 불러오기
from core.audit_agent.naver_verifier import NaverStoreVerifier

def run_naver_test():
    # 1. .env 파일에서 환경변수(API 키) 로드
    load_dotenv()
    
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    # 키가 제대로 들어왔는지 체크
    if not client_id or not client_secret:
        print("❌ 에러: .env 파일에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정해주세요.")
        return

    print("✅ API 키 로드 완료. 네이버 장소 검색 테스트를 시작합니다...\n")
    
    # 검증기 객체 생성
    verifier = NaverStoreVerifier(client_id, client_secret)

    # 2. 테스트 케이스 준비 (다양한 업종과 지역)
    test_cases = [
        {"store_name": "유니크로", "address": "서울 강남구 영동대로 513 코엑스몰 D112"},
        {"store_name": "코애휘", "address": "서울 금천구 가산디지털2로 101 101동 1층 127호"},
        {"store_name": "참숯닭갈구이", "address": "부산 동래구 안락로 27 (안락동) 1층"},
        {"store_name": "아무도모르는가짜가게1234", "address": "우주"}
    ]

    # 3. 테스트 실행 및 결과 출력
    for i, case in enumerate(test_cases, 1):
        store = case['store_name']
        address = case['address']
        
        print(f"▶️ [TEST {i}] 상호명: '{store}' / 주소: '{address}' 검색 중...")
        
        # get_store_category 함수 호출!
        result = verifier.get_store_category(store_name=store, address=address)
        
        # 결과를 보기 좋게 JSON 형태로 출력
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 50)

if __name__ == "__main__":
    run_naver_test()