"""
Audit Result Component - Display audit results and violations
"""

import streamlit as st
from typing import Dict, Any, List
from pathlib import Path
import sys

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import AUDIT_DECISION_COLORS


def render_audit_results(audit_result: Dict[str, Any], compact: bool = False):
    """
    Render audit results with violations

    Args:
        audit_result: Dictionary containing audit results
        compact: If True, show compact version
    """

    decision = audit_result.get('audit_decision', 'Unknown')
    violation_score = audit_result.get('violation_score', 0.0)
    violations = audit_result.get('violations', [])
    reasoning = audit_result.get('reasoning', '')

    # Determine status color
    status_type = AUDIT_DECISION_COLORS.get(decision, 'info')

    if not compact:
        # Full display
        st.markdown("### 🤖 AI 감사 결과")

        # Decision banner
        if decision == "Pass":
            st.success(f"### ✅ {decision}")
        elif decision == "Anomaly Detected":
            st.error(f"### ❌ {decision}")
        else:
            st.warning(f"### ⚠️ {decision}")

        # Score display
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("#### 위반 가능성 점수")
            st.progress(violation_score)
            st.markdown(f"<center><h2>{violation_score * 100:.1f}%</h2></center>", unsafe_allow_html=True)

        st.markdown("---")

        # Reasoning
        if reasoning:
            st.markdown("### 📋 판단 근거")
            st.info(reasoning)

        # Violations detail
        if violations:
            st.markdown("### 🚨 위반 항목 상세")

            for idx, violation in enumerate(violations, 1):
                with st.expander(f"위반 항목 #{idx} - 품목 ID: {violation.get('item_id', 'N/A')}", expanded=True):
                    st.markdown(f"**사유:** {violation.get('reason', 'N/A')}")

                    if 'policy_reference' in violation:
                        st.markdown("**관련 규정:**")
                        st.code(violation['policy_reference'], language=None)

                    # Severity indicator
                    severity = violation.get('severity', 'high')
                    severity_colors = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }
                    st.markdown(f"**심각도:** {severity_colors.get(severity, '⚪')} {severity.upper()}")

        else:
            st.success("✅ 위반 항목이 발견되지 않았습니다!")

    else:
        # Compact display
        col1, col2 = st.columns([1, 3])

        with col1:
            if decision == "Pass":
                st.success("✅ 통과")
            elif decision == "Anomaly Detected":
                st.error("❌ 위반 감지")
            else:
                st.warning("⚠️ 경고")

        with col2:
            st.metric("위반 가능성", f"{violation_score * 100:.1f}%")

        if violations:
            st.warning(f"⚠️ {len(violations)}개의 위반 항목이 발견되었습니다")
            for violation in violations:
                st.markdown(f"- {violation.get('reason', 'N/A')}")


def render_violation_table(violations: List[Dict[str, Any]]):
    """
    Render violations in a table format

    Args:
        violations: List of violation dictionaries
    """

    if not violations:
        st.info("위반 항목이 없습니다.")
        return

    import pandas as pd

    # Convert to DataFrame
    df_data = []
    for v in violations:
        df_data.append({
            '품목 ID': v.get('item_id', 'N/A'),
            '위반 사유': v.get('reason', 'N/A'),
            '심각도': v.get('severity', 'high').upper(),
        })

    df = pd.DataFrame(df_data)

    st.dataframe(df, use_container_width=True)


def render_policy_reference(policy_text: str):
    """
    Render policy reference section

    Args:
        policy_text: Policy text to display
    """

    with st.expander("📜 회계 규정 전문 보기"):
        st.markdown("### 학생 자치 기구 예산 사용 규정")
        st.text(policy_text)


def render_audit_summary_card(audit_result: Dict[str, Any]):
    """
    Render a summary card for audit results

    Args:
        audit_result: Dictionary containing audit results
    """

    decision = audit_result.get('audit_decision', 'Unknown')
    violation_score = audit_result.get('violation_score', 0.0)
    violations = audit_result.get('violations', [])

    # Card styling
    if decision == "Pass":
        bg_color = "#d4edda"
        border_color = "#28a745"
        icon = "✅"
    elif decision == "Anomaly Detected":
        bg_color = "#f8d7da"
        border_color = "#dc3545"
        icon = "❌"
    else:
        bg_color = "#fff3cd"
        border_color = "#ffc107"
        icon = "⚠️"

    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        border-left: 5px solid {border_color};
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    ">
        <h3>{icon} {decision}</h3>
        <p><strong>위반 가능성:</strong> {violation_score * 100:.1f}%</p>
        <p><strong>위반 항목 수:</strong> {len(violations)}개</p>
    </div>
    """, unsafe_allow_html=True)


def render_recommendations(audit_result: Dict[str, Any]):
    """
    Render recommendations based on audit results

    Args:
        audit_result: Dictionary containing audit results
    """

    violations = audit_result.get('violations', [])

    if not violations:
        st.success("""
        ### ✅ 권장 사항

        - 영수증이 회계 규정을 준수합니다
        - 최종 확정을 진행해주세요
        """)
    else:
        st.warning("""
        ### ⚠️ 권장 사항

        위반 항목이 감지되었습니다. 다음 조치를 권장합니다:

        1. **위반 항목 확인**: 위 목록에서 구체적인 위반 사유를 확인하세요
        2. **데이터 수정**: 잘못 인식된 경우 '데이터 편집' 탭에서 수정하세요
        3. **규정 검토**: 해당 지출이 정당한 경우 관리자와 상의하세요
        4. **재감사**: 수정 후 '감사 실행' 버튼을 다시 눌러주세요
        """)

        st.markdown("---")

        st.error("""
        **주의**: 위반 항목이 있는 영수증을 최종 확정할 경우,
        추후 감사 과정에서 문제가 될 수 있습니다.
        """)
