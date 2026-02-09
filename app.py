import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, time, timedelta

# --- HÀM TÍNH GIỜ LÀM VIỆC ---
def calculate_working_hours(start_dt, end_dt):
    if pd.isna(start_dt) or start_dt > end_dt:
        return 0
    total_seconds = 0
    curr = start_dt
    while curr.date() <= end_dt.date():
        if curr.weekday() < 5: 
            morn_s, morn_e = datetime.combine(curr.date(), time(8, 30)), datetime.combine(curr.date(), time(12, 0))
            aft_s, aft_e = datetime.combine(curr.date(), time(13, 30)), datetime.combine(curr.date(), time(18, 0))
            s_m, e_m = max(curr, morn_s), min(end_dt, morn_e)
            if s_m < e_m: total_seconds += (e_m - s_m).total_seconds()
            s_a, e_a = max(curr, aft_s), min(end_dt, aft_e)
            if s_a < e_a: total_seconds += (e_a - s_a).total_seconds()
        curr = (curr + timedelta(days=1)).replace(hour=8, minute=30, second=0)
    return total_seconds / 3600

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 1. Đọc dữ liệu (Tắt cache để cập nhật Start_time tức thì)
    raw_df = conn.read(spreadsheet=URL, header=None, ttl=0) 
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        
        # KIỂM TRA TÊN CỘT THỰC TẾ (DEBUG)
        # st.write("Danh sách cột hệ thống tìm thấy:", list(df.columns)) 

        # TỰ ĐỘNG KHỚP CỘT (Nếu bạn viết Start_Time hay start_time đều nhận)
        col_map = {c.lower(): c for c in df.columns}
        target_col = col_map.get('start_time')
        
        if target_col:
            df = df.rename(columns={target_col: 'Start_time'})
        else:
            df['Start_time'] = pd.NaT # Tạo cột trống nếu hoàn toàn không tìm thấy

        # Xử lý định dạng số & ngày tháng
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        df['Start_time'] = pd.to_datetime(df['Start_time'], errors='coerce')
        df['State_Clean'] = df['State'].fillna('None').str.strip
