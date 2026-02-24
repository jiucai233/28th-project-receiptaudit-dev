import json
import matplotlib.pyplot as plt

def evaluate_and_export_anomalies():
    input_file = "core/rag_engine/rag_test/rag_search_results.json"
    anomaly_output_file = "core/rag_engine/rag_test/anomaly_receipts.json"
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ '{input_file}' 파일을 찾을 수 없습니다.")
        return

    # --- [지표 1] 전체 영수증 대상 평균 규정 검색 성공률 (부분 점수 적용) ---
    total_receipts = len(data)
    total_rule_score = 0.0  # 비율(0.0 ~ 1.0)을 누적할 변수
    
    # --- [지표 2, 3] 위반(Anomaly) 영수증 대상 적발률 ---
    anomaly_receipts = []   
    first_detect_count = 0  
    top3_detect_count = 0   

    for item in data:
        # 1. 부분 점수 계산 (예: "2/3" -> 2 / 3 -> 0.666...)
        score_str = item.get("expected_rule_score", "0/3")
        try:
            num, denom = map(int, score_str.split('/'))
            if denom > 0:
                total_rule_score += (num / denom)
        except (ValueError, AttributeError):
            pass # 형식이 안 맞으면 0점 처리
            
        # 2. 위반(Anomaly) 데이터 분리 및 적발률 계산
        if "anomaly_detect" in item:
            anomaly_receipts.append(item)
            
            # 문자열 "True"이거나 불리언 True일 경우 모두 대응
            if str(item.get("anomaly_detect")).lower() == "true":
                top3_detect_count += 1
            if str(item.get("anomaly_first_detect")).lower() == "true":
                first_detect_count += 1

    # 퍼센트(%) 계산
    # 모든 영수증의 부분 점수를 더한 뒤 전체 개수로 나눔 (Mean Recall)
    rule_success_rate = (total_rule_score / total_receipts) * 100 if total_receipts > 0 else 0
    
    total_anomalies = len(anomaly_receipts)
    top3_success_rate = (top3_detect_count / total_anomalies) * 100 if total_anomalies > 0 else 0
    first_success_rate = (first_detect_count / total_anomalies) * 100 if total_anomalies > 0 else 0

    # 콘솔에 결과 출력
    print("="*55)
    print("📈 [RAG 검색 파이프라인 성능 평가 결과]")
    print(f"1. 전체 평균 규정 검색 성공률 (Mean Recall): {rule_success_rate:.1f}%")
    print("-" * 55)
    print(f"2. 위반 영수증 총 개수: {total_anomalies}개")
    print(f"   - 위반 규정 Top 3 포함 확률: {top3_success_rate:.1f}% ({top3_detect_count}/{total_anomalies})")
    print(f"   - 위반 규정 1위 도출 확률: {first_success_rate:.1f}% ({first_detect_count}/{total_anomalies})")
    print("="*55)

    # Anomaly 영수증만 따로 JSON으로 저장
    with open(anomaly_output_file, "w", encoding="utf-8") as f:
        json.dump(anomaly_receipts, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 위반(Anomaly) 영수증 {total_anomalies}개가 '{anomaly_output_file}'로 저장되었습니다!")

    # 발표용 시각화 막대그래프 생성
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    labels = [
        '평균 규정 검색 성공률\n(부분 점수 인정)', 
        '위반 규정 발견율\n(Top 3 포함)', 
        '위반 규정 1위 적중률\n(Top 1 도출)'
    ]
    values = [rule_success_rate, top3_success_rate, first_success_rate]
    colors = ['#3498db', '#e67e22', '#e74c3c']
    
    bars = ax.bar(labels, values, color=colors, width=0.5, alpha=0.9)
    ax.set_ylim(0, 125)
    ax.set_ylabel('성능 지표 (%)', fontsize=12, fontweight='bold')
    
    # 막대 위에 점수(%) 표시
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=13)

    plt.title('AI 감사 시스템 RAG 성능 평가', fontsize=15, pad=20)
    
    # 세부 정보 박스
    info_text = f"* 전체 영수증 테스트: {total_receipts}건\n* 위반 영수증 테스트: {total_anomalies}건"
    ax.text(0.03, 0.95, info_text, transform=ax.transAxes, fontsize=11, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig("core/rag_engine/rag_test/rag_final_metrics.png", dpi=300)
    print("📈 발표용 성능 그래프가 'rag_final_metrics.png'에 저장되었습니다!")

if __name__ == "__main__":
    evaluate_and_export_anomalies()