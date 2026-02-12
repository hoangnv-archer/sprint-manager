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
        # Ép kiểu datetime và xử lý nếu chỉ nhập mỗi Giờ mà thiếu Ngày
        start_dt = pd.to_datetime(start_val, errors='coerce')
        if pd.isna(start_dt):
            return 0
            
        # Nếu người dùng chỉ nhập "10:30", Python sẽ tự gán năm 1900. 
        # Chúng ta phải ép nó về ngày hôm nay.
        now_vn = datetime.now(VN_TZ)
        if start_dt.year < 2000: 
            start_dt = start_dt.replace(year=now_vn.year, month=now_vn.month, day=now_vn.day)

        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        
        diff = now_vn - start_dt
        actual_h = diff.total_seconds() / 3600
        return max(0, actual_h) 
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

st.set_page_config(page_title="Sprint Dashboard", layout="wide")

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = list(PROJECTS.keys())[0]

# --- SIDEBAR ---
for project_name in PROJECTS.keys():
    if st.sidebar.button(project_name, use_container_width=True, 
                         type="primary" if st.session_state.selected_project == project_name else "secondary"):
        st.session_state.selected_project = project_name
        st.rerun()

config = PROJECTS[st.session_state.selected_project]

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=config['url'], header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=config['url'], skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Ép kiểu số cho Estimate (Đơn vị: GIỜ)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace('None', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        t_col = next((c for c in df.columns if "start" in c.lower()), None)
        df['State_Clean'] = df['State'].fillna('').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # --- KIỂM TRA LỐ GIỜ ---
        over_est_list = []
        if t_col:
            for _, row in df_team.iterrows():
                # Kiểm tra trạng thái chứa chữ "progress"
                if 'progress' in row['State_Clean']:
                    actual_h = get_actual_hours(row[t_col])
                    est_h = float(row['Estimate Dev'])
                    
                    # Nếu thực tế trôi qua > dự kiến (đơn vị giờ)
                    if est_h > 0 and actual_h > est_h:
                        over_est_list.append({
                            "PIC": row['PIC'], 
                            "Task": row['Userstory/Todo'], 
                            "Thực tế": f"{round(actual_h, 2)}h", 
                            "Dự kiến": f"{round(est_h, 2)}h",
                            "Vượt": f"{round((actual_h - est_h)*60)} phút"
                        })

        st.title(f"🚀 {st.session_state.selected_project}")

        # Hiển thị thông báo đỏ
        if over_est_list:
            st.error(f"🚨 PHÁT HIỆN {len(over_est_list)} TASK LÀM QUÁ GIỜ DỰ KIẾN!")
            st.table(pd.DataFrame(over_est_list))
        else:
            st.success("✅ Không có task nào bị lố giờ hoặc chưa điền Start-time.")

        # --- DASHBOARD TRỰC QUAN ---
        pic_stats = df_team.groupby('PIC').agg(
            done=('State_Clean', lambda x: x.isin(['done', 'cancel', 'dev done']).sum()),
            total=('Userstory/Todo', 'count')
        ).reset_index()
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        cols = st.columns(len(pic_stats))
        for i, row in pic_stats.iterrows():
            cols[i].metric(row['PIC'], f"{row['percent']}%")
            cols[i].progress(row['percent']/100)

        st.subheader("📋 Chi tiết bảng dữ liệu")
        st.dataframe(df_team, use_container_width=True)

    else:
        st.error("Không tìm thấy tiêu đề 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi: {e}")
