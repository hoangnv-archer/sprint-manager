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
    
    # Chu kỳ 14 ngày (2 tuần)
    # Nếu days_diff âm (chưa tới ngày bắt đầu), vẫn trả về base_sprint_no
    sprint_elapsed = max(0, days_diff // 14)
    current_sprint_no = base_sprint_no + sprint_elapsed
    
    # Ngày bắt đầu của Sprint hiện tại
    current_sprint_start = base_date + timedelta(days=sprint_elapsed * 14)
    # Ngày kết thúc (Thứ 6 tuần sau = 11 ngày kể từ Thứ 2)
    current_sprint_end = current_sprint_start + timedelta(days=11)
    
    return current_sprint_no, current_sprint_start, current_sprint_end

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
        "sprint_start_date": "2026-02-09", # Ngày Thứ 2 bắt đầu Sprint
        "base_sprint_no": 1                # Số Sprint tại ngày bắt đầu đó
    },
    "Sprint Team Debuffer": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord",
        # Setup Sprint (So le 1 tuần):
        "sprint_start_date": "2026-02-16", # Thứ 2 tuần sau đó
        "base_sprint_no": 1
    }
}

st.set_page_config(page_title="Sprint Dashboard", layout="wide")

# --- 3. QUẢN LÝ CHỌN DỰ ÁN ---
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

st.sidebar.title("📁 Quản lý Sprint")

for project_name, p_config in PROJECTS.items():
    s_no, s_start, s_end = get_current_sprint_info(p_config)
    btn_label = f"{project_name}\n(Sprint {int(s_no)})"
    
    if st.sidebar.button(btn_label, use_container_width=True, 
                         type="primary" if st.session_state.selected_project == project_name else "secondary"):
        st.session_state.selected_project = project_name
        st.rerun()

# Lấy config hiện tại
config = PROJECTS[st.session_state.selected_project]
s_no, s_start, s_end = get_current_sprint_info(config)

# --- 4. XỬ LÝ DỮ LIỆU ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Chuẩn hóa số
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Trạng thái và PIC
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # Hiển thị tiêu đề động theo Sprint
        st.title(f"🚀 {st.session_state.selected_project}")
        
        # Thanh trạng thái thời gian Sprint
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            st.subheader(f"🔥 Sprint {int(s_no)}")
            st.caption(f"📅 Thời gian: {s_start.strftime('%d/%m/%Y')} ➔ {s_end.strftime('%d/%m/%Y')} (Kết thúc Thứ 6)")
        
        # Phần hiển thị cảnh báo lố giờ và thống kê giữ nguyên như bản trước...
        # (Để tiết kiệm không gian, tôi lược bớt phần vẽ Chart/Table phía dưới vì nó không đổi)
        
        # --- [PHẦN CODE HIỂN THỊ CẢNH BÁO VÀ BIỂU ĐỒ GIỐNG BẢN TRƯỚC] ---
        # ... (Bạn giữ nguyên phần logic over_est_list và pic_stats từ bản code cũ nhé)
        
    else:
        st.error("Không tìm thấy hàng tiêu đề trong Sheet.")
except Exception as e:
    st.error(f"Lỗi: {e}")
