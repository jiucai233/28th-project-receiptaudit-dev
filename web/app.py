"""
Transparent-Audit: 영수증 자동 감사 시스템
Frontend Main Application (Streamlit)
"""

import streamlit as st
from pathlib import Path
import sys

# Add src and project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(Path(__file__).parent / "src"))

from components.upload_component import render_upload_section
from components.data_editor_component import render_data_editor
from components.audit_result_component import render_audit_results
from utils.api_client import MockOCRClient as OCRClient, MockAuditClient as AuditClient, MOCK_RECEIPTS

def init_session_state():
    if 'receipt_data' not in st.session_state:
        st.session_state.receipt_data = None
    if 'audit_result' not in st.session_state:
        st.session_state.audit_result = None
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'demo_image' not in st.session_state:
        st.session_state.demo_image = None
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

def main():
    st.set_page_config(page_title="Transparent-Audit", page_icon="🧾", layout="wide")
    init_session_state()

    st.markdown('<h1 style="text-align: center; color: #1f77b4;">🧾 Transparent-Audit</h1>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("📋 Status")
        steps = {1: "Upload", 2: "Edit & Audit", 3: "Report"}
        for num, name in steps.items():
            st.markdown(f"{'🔵' if st.session_state.current_step == num else '⚪'} **Step {num}: {name}**")
        
        st.divider()
        st.header("🎯 Quick Demo")
        for scenario in MOCK_RECEIPTS.keys():
            if st.button(scenario, use_container_width=True):
                st.session_state.receipt_data = OCRClient().extract(scenario)
                st.session_state.audit_result = None
                st.session_state.generated_pdf = None
                st.session_state.current_step = 2
                
                kai_dir = Path(__file__).parent.parent / "data" / "raw" / "KAI"
                if kai_dir.exists():
                    import random
                    images = list(kai_dir.glob("*.png"))
                    if images: st.session_state.demo_image = random.choice(images)
                st.rerun()
        
        if st.button("🔄 Reset App", type="secondary", use_container_width=True):
            st.session_state.receipt_data = None
            st.session_state.audit_result = None
            st.session_state.generated_pdf = None
            st.session_state.current_step = 1
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["📤 Step 1: Upload", "🔍 Step 2: Audit", "📊 Step 3: Result"])

    with tab1:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("Upload Receipt")
            uploaded_file = render_upload_section()
            if uploaded_file:
                st.session_state.receipt_data = OCRClient().extract(list(MOCK_RECEIPTS.keys())[0])
                st.session_state.current_step = 2
                st.rerun()
        with col2:
            st.subheader("Preview")
            if st.session_state.demo_image:
                st.image(str(st.session_state.demo_image), use_container_width=True)

    with tab2:
        if st.session_state.receipt_data:
            st.subheader("Verify & Audit")
            st.session_state.receipt_data = render_data_editor(st.session_state.receipt_data)
            
            if st.button("🚀 Run AI Audit", type="primary"):
                with st.spinner("AI Analysis..."):
                    st.session_state.audit_result = AuditClient().check(st.session_state.receipt_data)
                    st.session_state.generated_pdf = None # Clear old PDF if data changed
            
            if st.session_state.audit_result:
                render_audit_results(st.session_state.audit_result)
                if st.button("Next to Final Report ➡️"):
                    st.session_state.current_step = 3
                    st.rerun()
        else:
            st.warning("Please start from Step 1.")

    with tab3:
        if st.session_state.audit_result:
            st.subheader("Final Report Generation")
            render_audit_results(st.session_state.audit_result, compact=True)
            
            st.divider()
            if st.button("📄 Generate Official PDF Report", type="primary"):
                with st.spinner("Creating PDF..."):
                    result = AuditClient().confirm(st.session_state.receipt_data, st.session_state.audit_result)
                    if result["status"] == "success":
                        st.session_state.generated_pdf = result
                        st.success(f"PDF Generated: {result['filename']}")
                    else:
                        st.error(f"Failed to generate PDF: {result.get('message')}")
            
            if st.session_state.generated_pdf:
                st.info("💡 Your report is ready for download.")
                st.download_button(
                    label="📥 Download Audit Report (PDF)",
                    data=st.session_state.generated_pdf["pdf_data"],
                    file_name=st.session_state.generated_pdf["filename"],
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("Audit result missing. Go to Step 2.")

if __name__ == "__main__":
    main()
