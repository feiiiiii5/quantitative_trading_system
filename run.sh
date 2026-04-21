#!/bin/bash
cd "$(dirname "$0")"
[ -d venv ] && source venv/bin/activate
streamlit run app.py --server.runOnSave true
