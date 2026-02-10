"""
Transparent-Audit: 영수증 자동 감사 시스템
Frontend Main Application (Streamlit)
"""

import streamlit as st
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from components.upload_component import render_upload_section
from components.data_editor_component import render_data_editor
from components.audit_result_component import render_audit_results

# Mock mode: Use sample data without backend server
# Change to real clients when backend is ready:
# from utils.api_client import OCRClient, AuditClient
from utils.api_client import MockOCRClient as OCRClient, MockAuditClient as AuditClient

# Page configuration
st.set_page_config(
    page_title="Transparent-Audit",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .step-indicator {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if 'receipt_data' not in st.session_state:
        st.session_state.receipt_data = None
    if 'audit_result' not in st.session_state:
        st.session_state.audit_result = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1

def main():
    """Main application flow"""
    init_session_state()

    # Header
    st.markdown('<div class="main-header">🧾 Transparent-Audit</div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #666;">조직 회계 투명성을 위한 스마트 영수증 감사 시스템</p>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("📋 진행 단계")
        steps = {
            1: "① 영수증 업로드",
            2: "② 데이터 확인 및 수정",
            3: "③ 감사 결과",
            4: "④ 최종 확정"
        }

        for step_num, step_name in steps.items():
            if st.session_state.current_step == step_num:
                st.markdown(f"**🔵 {step_name}**")
            else:
                st.markdown(f"⚪ {step_name}")

        st.markdown("---")
        st.markdown("### 📌 사용 방법")
        st.markdown("""
        1. 영수증 이미지를 업로드합니다
        2. OCR로 추출된 데이터를 확인하고 수정합니다
        3. '감사 실행' 버튼을 눌러 정책 위반을 검사합니다
        4. 최종 확정 후 PDF 보고서를 다운로드합니다
        """)

    # Main content area
    tab1, tab2, tab3 = st.tabs(["📤 업로드 & 추출", "✏️ 데이터 편집 & 감사", "📊 최종 결과"])

    with tab1:
        st.header("Step 1: 영수증 업로드")
        st.markdown("영수증 이미지를 업로드하면 자동으로 텍스트를 추출합니다.")

        # Upload component
        uploaded_file = render_upload_section()

        if uploaded_file:
            with st.spinner("🔍 OCR 처리 중..."):
                ocr_client = OCRClient()
                receipt_data = ocr_client.extract(uploaded_file)

                if receipt_data:
                    st.session_state.receipt_data = receipt_data
                    st.session_state.current_step = 2
                    st.success("✅ 데이터 추출 완료! '데이터 편집 & 감사' 탭으로 이동하세요.")
                    st.rerun()

    with tab2:
        if st.session_state.receipt_data is None:
            st.info("먼저 영수증을 업로드해주세요.")
        else:
            st.header("Step 2: 데이터 확인 및 수정")
            st.markdown("추출된 데이터를 확인하고 필요시 수정하세요.")

            # Data editor component
            edited_data = render_data_editor(st.session_state.receipt_data)
            st.session_state.receipt_data = edited_data

            st.markdown("---")
            st.header("Step 3: 감사 실행")

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("🔍 감사 실행", type="primary", use_container_width=True):
                    with st.spinner("🤖 AI 감사 진행 중..."):
                        audit_client = AuditClient()
                        audit_result = audit_client.check(st.session_state.receipt_data)

                        if audit_result:
                            st.session_state.audit_result = audit_result
                            st.session_state.current_step = 3
                            st.rerun()

            with col2:
                if st.button("🔄 데이터 초기화", use_container_width=True):
                    st.session_state.receipt_data = None
                    st.session_state.audit_result = None
                    st.session_state.current_step = 1
                    st.rerun()

            # Display audit results if available
            if st.session_state.audit_result:
                st.markdown("---")
                render_audit_results(st.session_state.audit_result)

    with tab3:
        if st.session_state.audit_result is None:
            st.info("먼저 감사를 실행해주세요.")
        else:
            st.header("Step 4: 최종 확정 및 보고서 생성")

            # Summary
            st.subheader("📋 감사 요약")
            render_audit_results(st.session_state.audit_result, compact=True)

            st.markdown("---")

            # Confirm button
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("✅ 최종 확정 및 PDF 생성", type="primary", use_container_width=True):
                    with st.spinner("📄 PDF 보고서 생성 중..."):
                        audit_client = AuditClient()
                        pdf_result = audit_client.confirm(
                            st.session_state.receipt_data,
                            st.session_state.audit_result
                        )

                        if pdf_result and 'pdf_url' in pdf_result:
                            st.success("✅ 보고서 생성 완료!")
                            st.session_state.current_step = 4

                            # Download button
                            st.download_button(
                                label="📥 PDF 다운로드",
                                data=pdf_result.get('pdf_data', b''),
                                file_name=f"audit_report_{st.session_state.receipt_data.get('receipt_id', 'unknown')}.pdf",
                                mime="application/pdf"
                            )

if __name__ == "__main__":
    main()
