import json
import time
import matplotlib.pyplot as plt
from pathlib import Path
from difflib import SequenceMatcher
from dotenv import load_dotenv

from core.audit_agent.reasoning import AuditReasoning

def _normalize(text: str) -> str:
    return text.replace(" ", "")

def _score_store_name(result: str, answer: str) -> float:
    if not answer: return 1.0 if not result else 0.0
    if not result: return 0.0
    if result == answer: return 1.0
    r, a = _normalize(result), _normalize(answer)
    if r == a: return 1.0
    if a in r or r in a: return max(len(min(r, a, key=len)) / len(max(r, a, key=len)), 0.8)
    return SequenceMatcher(None, r, a).ratio()

def _score_item(r_item: dict, a_item: dict) -> float:
    r_name, a_name = _normalize(r_item.get("name", "")), _normalize(a_item.get("name", ""))
    name_sim = SequenceMatcher(None, r_name, a_name).ratio()
    if name_sim < 0.4: return 0.0
    price_match = 1.0 if r_item.get("price") == a_item.get("price") else 0.0
    return name_sim * 0.5 + price_match * 0.5

def get_overall_accuracy(receipt: dict, answer: dict) -> float:
    s_store = _score_store_name(receipt.get("store_name", ""), answer.get("store_name", ""))
    result_items = receipt.get("items", [])
    answer_items = answer.get("items", [])
    
    total_item_score = 0.0
    max_items = max(len(result_items), len(answer_items))
    
    if not answer_items and not result_items:
        total_item_score = 1.0
        max_items = 1
    elif not result_items or not answer_items:
        total_item_score = 0.0
    else:
        used = set()
        for a_item in answer_items:
            best_score, best_idx = 0.0, -1
            for i, r_item in enumerate(result_items):
                if i in used: continue
                score = _score_item(r_item, a_item)
                if score > best_score:
                    best_score, best_idx = score, i
            if best_idx >= 0 and best_score > 0:
                used.add(best_idx)
            total_item_score += best_score

    total_entities = 1 + max_items
    return (s_store + total_item_score) / total_entities

def run_fixed_iteration_benchmark():
    load_dotenv()
    agent = AuditReasoning()
    
    result_path = Path("core/audit_agent/test/result.json")
    answer_path = Path("core/audit_agent/test/answer.json")
    
    with open(result_path, "r", encoding="utf-8") as f:
        ocr_results = json.load(f)
    with open(answer_path, "r", encoding="utf-8") as f:
        answers = json.load(f)

    TEST_COUNT = min(len(ocr_results), len(answers))
    MAX_ITER = 3

    avg_scores = {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
    
    json_results_log = []
    corrected_receipts_for_audit = [] 

    print(f"[과교정 방지 테스트] LLM 회차별 고정 교정 벤치마크 시작 (샘플 {TEST_COUNT}개)")

    for i in range(TEST_COUNT):
        receipt = ocr_results[i].copy()
        answer = answers[i]
        
        print(f"\n[{i+1}/{TEST_COUNT}] 상호명: {receipt.get('store_name')}")
        
        current_receipt = receipt
        receipt_history = {}
        start_time = time.time()
        
        acc_0 = get_overall_accuracy(current_receipt, answer)
        avg_scores[0] += acc_0
        receipt_history[0] = {"acc": acc_0, "data": current_receipt.copy()}
        print(f"  - 0회차(원본) 정확도: {acc_0*100:.1f}%")

        for iter_num in range(1, MAX_ITER + 1):
            current_receipt = agent.correct_receipt(current_receipt)
            current_acc = get_overall_accuracy(current_receipt, answer)
            
            avg_scores[iter_num] += current_acc
            receipt_history[iter_num] = {"acc": current_acc, "data": current_receipt.copy()}
            print(f"  - {iter_num}회차 교정 후 정확도: {current_acc*100:.1f}%")

        elapsed = time.time() - start_time
        corrected_receipts_for_audit.append(receipt_history[1]["data"])

        json_results_log.append({
            "receipt_id": answer.get("receipt_id"),
            "latency_seconds": round(elapsed, 2),
            "accuracies": {
                "0_original": round(receipt_history[0]["acc"] * 100, 2),
                "1_iter": round(receipt_history[1]["acc"] * 100, 2),
                "2_iter": round(receipt_history[2]["acc"] * 100, 2),
                "3_iter": round(receipt_history[3]["acc"] * 100, 2),
            },
            "data_history": {
                "0_original": {"store_name": receipt_history[0]["data"].get("store_name"), "items": receipt_history[0]["data"].get("items")},
                "1_iter": {"store_name": receipt_history[1]["data"].get("store_name"), "items": receipt_history[1]["data"].get("items")},
                "2_iter": {"store_name": receipt_history[2]["data"].get("store_name"), "items": receipt_history[2]["data"].get("items")},
                "3_iter": {"store_name": receipt_history[3]["data"].get("store_name"), "items": receipt_history[3]["data"].get("items")},
            },
            "ground_truth": {"store_name": answer.get("store_name"), "items": answer.get("items")}
        })

    output_json_path = "core/audit_agent/test/proofread_benchmark_results.json"
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(json_results_log, f, ensure_ascii=False, indent=2)

    audit_input_path = "core/audit_agent/test/test_corrected_ocr.json"
    with open(audit_input_path, "w", encoding="utf-8") as f:
        json.dump(corrected_receipts_for_audit, f, ensure_ascii=False, indent=2)

    final_avg = [
        (avg_scores[0] / TEST_COUNT) * 100,
        (avg_scores[1] / TEST_COUNT) * 100,
        (avg_scores[2] / TEST_COUNT) * 100,
        (avg_scores[3] / TEST_COUNT) * 100
    ]

    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False

    fig, ax = plt.subplots(figsize=(10, 6))
    
    labels = ['원본 (0회차)', '1회 교정', '2회 교정', '3회 교정']
    colors = ['#95a5a6', '#3498db', '#f39c12', '#e74c3c'] 
    
    bars = ax.bar(labels, final_avg, color=colors, width=0.5, alpha=0.9)
    ax.set_ylim(0, 110)
    ax.set_ylabel('영수증 평균 정확도 (%)', fontsize=12, fontweight='bold')
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 1, f'{yval:.1f}%', ha='center', va='bottom', fontsize=13, fontweight='bold')

    plt.title(f'LLM 교정 횟수에 따른 오타 수정 정확도 추이 (샘플 {TEST_COUNT}개)', fontsize=15, pad=20)
    
    ax.text(0.02, 0.95, '* 과교정(Hallucination) 현상 관찰용 데이터', transform=ax.transAxes, fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    save_path = "core/audit_agent/test/proofread_iteration_comparison.png"
    plt.savefig(save_path, dpi=300)
    print(f"\n비교 그래프가 '{save_path}'에 저장되었습니다.")

if __name__ == "__main__":
    run_fixed_iteration_benchmark()