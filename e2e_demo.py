import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# OCR Engine
from core.ocr_engine.paddle_wrapper import PaddleOCRWrapper
from core.ocr_engine.processor import ReceiptProcessor

# RAG & Audit Engine
from core.audit_agent.reasoning import AuditReasoning
from core.audit_agent.prompt_templates import AUDIT_SYSTEM_PROMPT
from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager

def print_step(step_num, title, content=""):
    print(f"\n{'='*60}")
    print(f" [STEP {step_num}] {title}")
    print(f"{'='*60}")
    if content:
        print(content)
        print("-" * 60)

def run_e2e_demo():
    load_dotenv()
    
    # === Initialize Modules ===
    print("모듈 초기화 중... (OCR 배포 모델, RAG 벡터 DB, LLM 에이전트 등)")
    
    ocr_wrapper = PaddleOCRWrapper()
    processor = ReceiptProcessor()
    
    agent = AuditReasoning()
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()
    
    # === Test Cases ===
    test_cases = [
        {
            "label": "[정상 영수증 (일반 식당)]",
            "image_path": "data/raw/receipt-0140302be513.jpg",
            "expected": "Pass"
        },
        {
            "label": "[규정 위반 영수증 (주류 결제)]",
            "image_path": "data/raw/alchohol/Alcho_001.jpg", 
            "expected": "Anomaly Detected"
        }
    ]
    
    for idx, case in enumerate(test_cases):
        print(f"\n\n\n{'#'*80}")
        print(f"  테스트 케이스 {idx+1}: {case['label']}")
        print(f"  이미지 경로: {case['image_path']}")
        print(f"  예상 결과: {case['expected']}")
        print(f"{'#'*80}")
        
        # ---------------------------------------------------------
        # STEP 1: OCR Extraction & Parsing
        # ---------------------------------------------------------
        print_step(1, "OCR 텍스트 추출 및 영수증 구조화 (PaddleOCR + Regex/Heuristics)")
        start_time = time.time()
        try:
            # 1. PaddleOCR 텍스트 추출
            ocr_lines = ocr_wrapper.extract(case['image_path'])
            # 2. 파서(Processor)를 통해 JSON 구조화
            receipt_json = processor.process(ocr_lines)
            
            ocr_time = time.time() - start_time
            print(f"✅ OCR 및 파싱 성공 ({ocr_time:.2f}초)")
            print("\n[추출된 영수증 데이터(JSON)]")
            print(json.dumps(receipt_json, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"❌ OCR/Parsing 실패: {e}")
            continue

        store_name = receipt_json.get("store_name", "")
        store_address = receipt_json.get("store_address", "")
        items = receipt_json.get("items", [])
        
        if not store_name and not items:
            print("⚠️ 영수증 데이터가 너무 부족하여(상호명/내역 없음) 감사를 건너뜁니다.")
            continue
            
        # ---------------------------------------------------------
        # STEP 2: Naver API Cross Validation (Tools)
        # ---------------------------------------------------------
        print_step(2, "외부 도구(Naver API)를 활용한 가맹점 업종 교차 검증 (Agent Tool Use)")
        print(f"검색 쿼리: '{store_name} {store_address.split(' ')[0] if store_address else ''}'")
        
        store_info = agent.verifier.get_store_category(store_name, store_address)
        
        print("\n[네이버 장소 API 검증 결과]")
        print(json.dumps(store_info, ensure_ascii=False, indent=2))
        if store_info.get("category_full"):
            print(f"💡 시스템 인지: 이 가게의 실제 업종은 [{store_info['category_full']}] 입니다.")
        elif store_info.get("error"):
            print(f"⚠️ 네이버 검색 실패: {store_info['error']} (상호명만으로 감사를 진행합니다.)")

        # ---------------------------------------------------------
        # STEP 3: RAG Retrieval + LLM Re-ranking
        # ---------------------------------------------------------
        print_step(3, "RAG: 영수증 품목 기반 관련 사내(법인) 규정 탐색 및 LLM Re-ranking")
        
        rules_rerank_list = []
        unique_contents = set()
        
        print("품목별 관련 규정 검색 중...")
        for item in items:
            item_name = item.get('name', '')
            query = f"가게: {store_name}, 품목: {item_name}"
            
            # search_rules 안에 Agent LLM을 넣으면 자동으로 Re-ranking을 수행함
            try:
                docs = db_manager.search_rules(query, embedder.get_embedding_model(), k=3, agent_llm=agent.llm)
                for d in docs:
                    if d.page_content not in unique_contents:
                        rules_rerank_list.append(d.page_content)
                        unique_contents.add(d.page_content)
                print(f" └ [✔️] '{item_name}' ➡ 추출된 관련 규정 {len(docs)}개")
            except Exception as e:
                print(f" └ [❌] '{item_name}' ➡ RAG 검색 중 에러: {e}")
                
        rules_text = "\n\n".join(rules_rerank_list)
        
        print("\n[에이전트에게 제공될 최종 규정(Context) 요약]")
        if rules_text:
            lines = rules_text.split('\n')
            preview = '\n'.join(lines) if len(lines) <= 5 else '\n'.join(lines[:5]) + "\n... (중략)"
            print(preview)
        else:
            print("관련 규정을 찾지 못했습니다.")

        # ---------------------------------------------------------
        # STEP 4: Final LLM Decision (Audit Agent)
        # ---------------------------------------------------------
        print_step(4, "최종 감사 추론 (Final LLM Reasoning: Solar-1-Mini)")
        
        # 프롬프트 조립
        final_prompt = f"{AUDIT_SYSTEM_PROMPT}\n\n상호명: {store_name}\n가맹점 업종(네이버): {json.dumps(store_info, ensure_ascii=False)}\n규정: {rules_text}\n\n영수증: {json.dumps(receipt_json, ensure_ascii=False)}"
        
        print("LLM이 수집된 정보(OCR 영수증 + 외부 API 가맹점 + RAG 사내규정)를 종합하여 결정을 내리고 있습니다...\n")
        
        try:
            start_time = time.time()
            prompt_obj = agent.llm.invoke(final_prompt)
            final_decision_json = agent.parser.invoke(prompt_obj)
            llm_time = time.time() - start_time
            
            print(f"✅ 의사결정 완료 ({llm_time:.2f}초)")
            
            print("\n================ FINAL REPORT ================")
            print(f"🎯 최종 판정: {final_decision_json.get('audit_decision', 'N/A')}")
            print(f"🚩 위반 확률 점수: {final_decision_json.get('violation_score', 'N/A')}/100")
            print(f"📝 사유 및 해석:")
            print(f"   {final_decision_json.get('reason_for_decision', '설명 없음')}")
            print("==============================================")
            
        except Exception as e:
            print(f"❌ LLM 추론 실패: {e}")

    print("\n\n🎉 End-to-End 데모 스트립트가 완전히 종료되었습니다.")

if __name__ == "__main__":
    # 라이브러리 경고(Warning) 제거를 위해 os.environ 설정 필요 시 추가
    import warnings
    warnings.filterwarnings("ignore")
    run_e2e_demo()
