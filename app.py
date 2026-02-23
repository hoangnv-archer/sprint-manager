import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_current_sprint_info(config):
    """
    Tính toán Sprint dựa trên ngày bắt đầu được setup riêng cho từng dự án
    """
    now = datetime.now(VN_TZ).date()
    # Lấy ngày bắt đầu và số Sprint gốc từ config
    base_date = datetime.strptime(config['sprint_start_date'], "%Y-%m-%d").date()
    base_sprint_no = config['base_sprint_no']
    
    # Tính số ngày đã trôi qua kể từ mốc setup
    days_diff = (now - base_date).days
    
    # Chu kỳ 14 ngày (2 tuần). max(0) để tránh số âm nếu setup ngày tương lai
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = base_sprint_no + sprint_elapsed
    
    # Ngày bắt đầu của Sprint hiện tại
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    # Ngày kết thúc (Thứ 6 tuần sau = 11 ngày kể từ Thứ 2)
    current_sprint_end = current_sprint_start + timedelta(days=11)
    
    return current_sprint_no, current_sprint_start, current_sprint_end

def get_actual_hours(start_val):
    if pd.isna(start_val) or str(start_val).strip().lower() in ['none', '', 'nat', 'nan']:
        return 0
    try:
        start_dt = pd.to_datetime(start_val, errors='coerce')
        if pd.isna(start_dt): return 0
        now_vn = datetime.now(VN_TZ)
        if start_dt.year < 2000: 
            start_dt = start_dt.replace(year=now_vn.year, month=now_vn.month, day=now_vn.day)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        return max(0, (now_vn - start_dt).total_seconds() / 3600)
    except: return 0

# --- 2. CẤU HÌNH DỰ ÁN (SETUP TẠI ĐÂY) ---
PROJECTS = {
    "Sprint Team Infinity": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251,
        # Setup Sprint:
        "sprint_start_date": "2026-02-09", 
        "base_sprint_no": 1                
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        # Setup Sprint (So le):
        "sprint_start_date": "2026-02-16", 
        "base_sprint_no": 1
    }
}

st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# --- 3. SIDEBAR ---
st.sidebar.title("📁 Quản lý Sprint")
for project_name, p_config in PROJECTS.items():
    s_no, s_start, s_end = get_current_sprint_info(p_config)
    btn_label = f"{project_name}\n(Sprint {int(s_no)})"
    if st.sidebar.button(btn_label, use_container_width=True, 
                         type="primary" if st.session_state.selected_project == project_name else "secondary"):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]
s_no, s_start, s_end = get_current_sprint_info(config)

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df
