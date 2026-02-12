import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_actual_hours(start_val):
    if pd.isna(start_val) or str(start_val).strip().lower() in ['none', '', 'nat', 'nan']:
        return 0
    try:
        # Ép kiểu datetime
        start_dt = pd.to_datetime(start_val, errors='coerce')
        if pd.isna(start_dt):
            return 0
            
        # Xử lý nếu PIC chỉ nhập giờ (ví dụ 10:30) mà thiếu ngày
        now_vn = datetime.now(VN_TZ)
        if start_dt.year < 2000: 
            start_dt = start_dt.replace(year=now_vn.year, month=now_vn.month, day=now_vn.day)

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        
        diff = now_vn - start_dt
        return max(0, diff.total_seconds() / 3600) 
    except:
        return 0

# --- 2. CẤU HÌNH ---
PROJECTS = {
    "Sprint Team 2": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251
    },
    "Sprint Dashboard Final": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord"
    }
}

st.set_page_config(page_title="Sprint Multi-Project Dashboard", layout="wide")

# --- 3. SIDEBAR CHỌN DỰ ÁN ---
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

st.sidebar.title("📁 Danh sách dự án")
for project_name in PROJECTS.keys():
    btn_type = "primary" if st.session_state.selected_project == project_name else "secondary"
    if st.sidebar.button(project_name, use_container_width=True, type=btn_type):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=G
