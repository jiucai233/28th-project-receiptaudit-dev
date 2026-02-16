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
from utils.api_client import OCRClient, MockAuditClient as AuditClient, MOCK_RECEIPTS, MockOCRClient

def init_session_state():
    if 'receipts_list' not in st.session_state:
        st.session_state.receipts_list = []
    if 'current_receipt_index' not in st.session_state:
        st.session_state.current_receipt_index = 0
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
    if 'generated_pdf' not in st.session_state:
        st.session_state.generated_pdf = None

@st.cache_data(show_spinner=False)
def call_ocr_api(uploaded_file_bytes, file_name, file_type):
    """Cached OCR API call to prevent redundant processing"""
    class MockUploadedFile:
        def __init__(self, content, name, type):
            self.content = content
            self.name = name
            self.type = type
        def getvalue(self):
            return self.content
            
    mock_file = MockUploadedFile(uploaded_file_bytes, file_name, file_type)
    return OCRClient().extract(mock_file)

def main():
    st.set_page_config(page_title="Transparent-Audit", page_icon="🧾", layout="wide")
    init_session_state()

    st.markdown('<h1 style="text-align: center; color: #1f77b4;">🧾 Transparent-Audit</h1>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("📋 Status")
        steps = {1: "Upload", 2: "Edit & Audit", 3: "Report"}
        for num, name in steps.items():
            st.markdown(f"{'🔵' if st.session_state.current_step == num else '⚪'} **Step {num}: {name}**")
        
        if st.session_state.receipts_list:
            st.divider()
            st.header("📂 Receipts")
            for idx, r in enumerate(st.session_state.receipts_list):
                label = f"{idx+1}. {r.get('store_name', 'Unknown')}"
                if st.button(label, key=f"nav_{idx}", use_container_width=True, 
                             type="primary" if st.session_state.current_receipt_index == idx else "secondary"):
                    st.session_state.current_receipt_index = idx
                    st.session_state.current_step = 2
                    st.rerun()

        st.divider()
        st.header("🎯 Quick Demo")
        for scenario in MOCK_RECEIPTS.keys():
            if st.button(scenario, use_container_width=True):
                data = MockOCRClient().extract(scenario)
                st.session_state.receipts_list = [data]
                st.session_state.current_receipt_index = 0
                st.session_state.generated_pdf = None
                st.session_state.current_step = 2
                st.rerun()
        
        if st.button("🔄 Reset App", type="secondary", use_container_width=True):
            st.session_state.receipts_list = []
            st.session_state.current_receipt_index = 0
            st.session_state.generated_pdf = None
            st.session_state.current_step = 1
            st.cache_data.clear() # Clear OCR cache on reset
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["📤 Step 1: Upload", "🔍 Step 2: Audit", "📊 Step 3: Result"])

    with tab1:
        st.subheader("Upload Receipts")
        uploaded_input = render_upload_section()
        if uploaded_input:
            # Ensure it's a list even if Streamlit returns a single object
            uploaded_files = uploaded_input if isinstance(uploaded_input, list) else [uploaded_input]
            
            if st.button(f"🔍 Start OCR Analysis ({len(uploaded_files)} files)", type="primary", use_container_width=True):
                new_receipts = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {i+1}/{len(uploaded_files)}: {file.name}...")
                    result = call_ocr_api(file.getvalue(), file.name, file.type)
                    if result:
                        new_receipts.append(result)
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                if new_receipts:
                    st.session_state.receipts_list = new_receipts
                    st.session_state.current_receipt_index = 0
                    st.success(f"✅ Successfully processed {len(new_receipts)} receipts!")
                    st.balloons()
                    import time
                    time.sleep(1)
                    st.session_state.current_step = 2
                    st.rerun()

    with tab2:
        if st.session_state.receipts_list:
            idx = st.session_state.current_receipt_index
            receipt_data = st.session_state.receipts_list[idx]
            
            st.subheader(f"Verify & Audit ({idx+1}/{len(st.session_state.receipts_list)})")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                # Store the updated data back to list
                st.session_state.receipts_list[idx] = render_data_editor(receipt_data)
            with col2:
                if receipt_data.get("full_image_url"):
                    st.image(receipt_data["full_image_url"], use_container_width=True)
                else:
                    st.info("No image preview available")

            if st.button("🚀 Run AI Audit for this Receipt", type="primary"):
                with st.spinner("AI Analysis..."):
                    st.session_state.receipts_list[idx]["audit_result"] = AuditClient().check(st.session_state.receipts_list[idx])
            
            audit_res = st.session_state.receipts_list[idx].get("audit_result")
            if audit_res:
                render_audit_results(audit_res)
                
                col_nav1, col_nav2 = st.columns(2)
                with col_nav1:
                    if idx > 0:
                        if st.button("⬅️ Previous Receipt"):
                            st.session_state.current_receipt_index -= 1
                            st.rerun()
                with col_nav2:
                    if idx < len(st.session_state.receipts_list) - 1:
                        if st.button("Next Receipt ➡️"):
                            st.session_state.current_receipt_index += 1
                            st.rerun()
                    else:
                        if st.button("Final Report ➡️"):
                            st.session_state.current_step = 3
                            st.rerun()
        else:
            st.warning("Please upload receipts first.")

    with tab3:
        if st.session_state.receipts_list:
            st.subheader("Batch Report Summary")
            all_passed = True
            for i, r in enumerate(st.session_state.receipts_list):
                audit_res = r.get("audit_result")
                status = audit_res.get("audit_decision", "Not Audited") if audit_res else "Not Audited"
                st.write(f"**{i+1}. {r.get('store_name')}**: {status}")
                if status != "Pass": all_passed = False

            st.divider()
            if st.button("📄 Generate Batch Report (Combined)", type="primary"):
                with st.spinner("Creating Report..."):
                    # For now, generate report for current one or implement batch logic
                    idx = st.session_state.current_receipt_index
                    r_data = st.session_state.receipts_list[idx]
                    a_res = r_data.get("audit_result")
                    if a_res:
                        result = AuditClient().confirm(r_data, a_res)
                        if result["status"] == "success":
                            st.session_state.generated_pdf = result
                            st.success(f"Report Generated for {r_data.get('store_name')}")
                        else:
                            st.error(f"Failed: {result.get('message')}")
                    else:
                        st.error("Current receipt has not been audited.")
            
            if st.session_state.generated_pdf:
                st.download_button(
                    label="📥 Download Audit Report (PDF)",
                    data=st.session_state.generated_pdf["pdf_data"],
                    file_name=st.session_state.generated_pdf["filename"],
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.warning("No data available.")

if __name__ == "__main__":
    main()
