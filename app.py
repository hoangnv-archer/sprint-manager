import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta, timezone

# --- 1. CÀI ĐẶT MÚI GIỜ VIỆT NAM ---
# Ép kiểu múi giờ để tránh việc Server chạy giờ quốc tế làm sai lệch cảnh báo
VN_TZ = timezone(timedelta(hours=7))

def get_actual_hours_vn(start_dt):
    if pd.isna(start_dt):
        return 0
    # Chuyển start_dt sang múi giờ VN nếu chưa có
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=VN_TZ)
    now_vn = datetime.now(VN_TZ)
    duration = now_vn - start_dt
    return max(0, duration.total_seconds() / 3600)

st.set_page_config(page_title="Sprint Workload Analyzer", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    # 2. ĐỌC VÀ XỬ LÝ TIÊU ĐỀ CỘT
    raw_df = conn.read(spreadsheet=URL, header=None, ttl=0)
    header_idx = next((i for i, row in raw_df.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # --- FIX: XỬ LÝ DẤU PHẨY TRONG SỐ THẬP PHÂN ---
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').replace('None', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # --- FIX: DÒ TÌM CỘT START_TIME (Cột I) ---
        # Tự động tìm cột chứa chữ "Start" hoặc dùng vị trí cột 9
        start_col = next((c for c in df.columns if "start" in c.lower()), None)
        if not start_col and len(df.columns) >= 9:
            start_col = df.columns[8]
            
        if start_col:
            df['Start_DT'] = pd.to_datetime(df[start_col], errors='coerce')
        else:
            df['Start_DT'] = pd.NaT

        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # 3. TÍNH TOÁN CẢNH BÁO (OVER ESTIMATE)
        over_est_list = []
        for _, row in df_team.iterrows():
            if 'progress' in row['State_Clean'] and not pd.isna(row['Start_DT']):
                actual_h = get_actual_hours_vn(row['Start_DT'])
                est_h = float(row['Estimate Dev'])
                # So sánh: Nếu làm lố dù chỉ 1 phút
                if est_h > 0 and actual_h > est_h:
                    over_est_list.append({
                        "PIC": row['PIC'], "Task": row['Userstory/Todo'], 
                        "Actual": round(actual_h, 2), "Est": est_h
                    })

        st.title("🚀 Sprint Performance Dashboard")

        # Hiển thị bảng cảnh báo lỗi
        if over_est_list:
            st.error(f"🚨 CẢNH BÁO: {len(over_est_list)} Task đang vượt quá Estimate!")
            st.table(pd.DataFrame(over_est_list))
        else:
            st.success("✅ Mọi task In Progress đều đang trong thời gian cho phép.")

        # 4. KHÔI PHỤC TOÀN BỘ STATS CŨ
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            real_h=('Real', 'sum'),
            est_h=('Estimate Dev', 'sum')
        ).reset_index()
        pic_stats['remain'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        # Giao diện Metrics
        st.subheader("👤 Thống kê theo PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"#### **{row['PIC']}**")
                st.metric("Hoàn thành", f"{row['percent']}%")
                st.write(f"✅ Xong: {int(row['done'])} | 🚧 Làm: {int(row['doing'])}")
                st.write(f"⏳ Còn lại: **{int(row['remain'])}**")
                st.progress(min(row['percent']/100, 1.0))
                st.divider()

        # 5. GỬI DISCORD (Gồm cả Báo cáo và Cảnh báo)
        st.sidebar.subheader("📢 Discord Webhook")
        webhook_url = st.sidebar.text_input("Webhook URL:", type="password")
        if st.sidebar.button("📤 Gửi báo cáo chi tiết"):
            if webhook_url:
                msg = "📊 **SPRINT REPORT - VIETNAM TIME**\n━━━━━━━━━━━━━━━━━━━━━\n"
                for _, r in pic_stats.iterrows():
                    msg += f"👤 **{r['PIC']}**: `{r['percent']}%` (Xong {int(r['done'])}/{int(r['total'])})\n"
                
                msg += "\n🚨 **CẢNH BÁO VƯỢT GIỜ:**\n"
                if over_est_list:
                    for item in over_est_list:
                        msg += f"🔥 `{item['PIC']}` lố: **{item['Task']}** (`{item['Actual']}h`/{item['Est']}h)\n"
                else:
                    msg += "✅ Không có task nào vượt Estimate.\n"
                
                requests.post(webhook_url, json={"content": msg})
                st.sidebar.success("Đã gửi báo cáo thành công!")

        # 6. BIỂU ĐỒ & BẢNG CHI TIẾT
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_h', 'real_h'], barmode='group', title="So sánh Estimate vs Real (Giờ)"), use_container_width=True)
        st.subheader("📋 Danh sách Task chi tiết")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real', 'Start_DT']], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng tiêu đề 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
