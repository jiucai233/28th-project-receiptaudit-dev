@echo off
echo Starting Receipt Audit Backend...
set PYTHONPATH=%CD%

@rem Disable oneDNN/MKLDNN to avoid NotImplementedError on Windows
set FLAGS_use_onednn=0
set FLAGS_use_mkldnn=0
set KMP_DUPLICATE_LIB_OK=TRUE

@rem Disable new PIR executor if it's causing attribute conversion issues
set FLAGS_enable_pir_api=0

call .venv\Scripts\activate
python -m uvicorn server.routes.app:app --host 0.0.0.0 --port 8000 --reload --reload-dir server
pause
