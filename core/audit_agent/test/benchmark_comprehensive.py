import json
import time
import matplotlib.pyplot as plt
from pathlib import Path
from dotenv import load_dotenv

from core.audit_agent.reasoning import AuditReasoning
from core.rag_engine.embedder import RegulationEmbedder
from core.rag_engine.vector_db import VectorDBManager

def run_comprehensive_benchmark():
    load_dotenv()
    agent = AuditReasoning()
    
    print("[1단계] Vector DB를 로드합니다...")
    embedder = RegulationEmbedder()
    db_manager = VectorDBManager()

    # Load Data
    with open("core/audit_agent/test/test_answers_with_expected.json", "r", encoding="utf-8") as f:
        answers = json.load(f)
    with open("core/audit_agent/test/result.json", "r", encoding="utf-8") as f:
        raw_ocrs = json.load(f)
    with open("core/audit_agent/test/test_corrected_ocr.json", "r", encoding="utf-8") as f:
        corrected_ocrs = json.load(f)

    # test_corrected_ocr.json might be shorter, take the minimum length to align
    TEST_COUNT = min(len(answers), len(raw_ocrs), len(corrected_ocrs))
    # We can cap TEST_COUNT if we want to run it fast, but for comprehensive let's do all
    print(f" [2단계] 풀 파이프라인 5가지 방식 비교 벤치마크 시작 (샘플 {TEST_COUNT}개)\n")

    methods = [
        {"id": "M1", "name": "정답 데이터 (Ground Truth)", "source": "answers", "use_naver": False},
        {"id": "M2", "name": "단순 OCR", "source": "raw_ocrs", "use_naver": False},
        {"id": "M3", "name": "단순 OCR + 네이버 검색", "source": "raw_ocrs", "use_naver": True},
        {"id": "M4", "name": "LLM 교정 OCR", "source": "corrected_ocrs", "use_naver": False},
        {"id": "M5", "name": "풀 파이프라인(교정+네이버)", "source": "corrected_ocrs", "use_naver": True}
    ]

    metrics = {m["id"]: {"correct": 0} for m in methods}
    
    for i in range(TEST_COUNT):
        ans_data = answers[i]
        corr_data = corrected_ocrs[i]
        raw_data = raw_ocrs[i]

        data_map = {
            "answers": ans_data,
            "raw_ocrs": raw_data,
            "corrected_ocrs": corr_data
        }
        
        expected = ans_data.get("expected", "Pass") 
        store_name = ans_data.get("store_name", f"영수증 {i+1}")
        print(f"[{i+1}/{TEST_COUNT}] {store_name} (목표 정답: {expected})")

        for m in methods:
            source_data = data_map[m["source"]]
            
            # 1. 문서 검색(RAG)
            query_json = json.dumps(source_data, ensure_ascii=False)
            retrieved_docs = db_manager.search_rules(query_json, embedder.get_embedding_model(), k=3)
            rules_text = "\n\n".join(doc.page_content for doc in retrieved_docs)
            
            # 2. 에이전트 평가
            try:
                res = agent.analyze(source_data, retrieved_rules=rules_text, use_naver=m["use_naver"])
                decision = res.get('audit_decision', "Pass")
            except Exception as e:
                print(f"  [{m['name']}] 평가 오류: {e}")
                decision = "Error"
                
            is_correct = (decision == expected)
            if is_correct:
                metrics[m["id"]]["correct"] += 1
            
            mark = "✅" if is_correct else "❌"
            print(f"   {mark} [{m['name']}] 판정: {decision}")

        print("-" * 50)
        
    with open("core/audit_agent/test/comprehensive_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # 시각화 부분
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    accuracies = [(metrics[m["id"]]["correct"] / TEST_COUNT) * 100 for m in methods]
    labels = [m["name"].replace(" ", "\n", 1) for m in methods] # 줄바꿈 추가
    
    colors = ['#2ecc71', '#95a5a6', '#f39c12', '#3498db', '#e74c3c']
    
    bars = ax.bar(labels, accuracies, color=colors, width=0.6)
    
    ax.set_ylim(0, 110)
    ax.set_ylabel('감사 정답률 (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'RAG 기반 AI 감사관 파이프라인 구성별 정답률 비교 (샘플 {TEST_COUNT}개)', fontsize=16, pad=20)

    # 막대 위 수치 표시
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 1.5, f'{yval:.1f}%', ha='center', va='bottom', fontsize=12, fontweight='bold')
        
    # 축 격자 추가
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    save_path = "core/audit_agent/test/comprehensive_benchmark.png"
    plt.savefig(save_path, dpi=300)
    print(f"\n최종 비교 그래프가 '{save_path}'에 저장되었습니다.")

if __name__ == "__main__":
    run_comprehensive_benchmark()
