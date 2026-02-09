import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta, timezone

# --- 1. CẤU HÌNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def calculate_actual_minutes(start_val):
    if pd.isna(start_val) or str(start_val).lower() in ['none', '']:
        return 0
    try:
        # Chuyển đổi Start_DT sang datetime và gán múi giờ VN
        start_dt = pd.to_datetime(start_val)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        now_vn = datetime.now(VN_TZ)
        diff = now_vn - start_dt
        return diff.total_seconds() / 60
    except:
        return 0

st.set_page_config(page_title="Sprint Analyzer Final", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)
URL = "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592"

try:
    df_raw = conn.read(spreadsheet=URL, header=None, ttl=0)
    header_idx = next((i for i, row in df_raw.iterrows() if "Userstory/Todo" in row.values), None)
            
    if header_idx is not None:
        df = conn.read(spreadsheet=URL, skiprows=header_idx, ttl=0)
        df.columns = [str(c).strip() for c in df.columns]

        # Xử lý số liệu (Dấu phẩy -> Dấu chấm)
        for col in ['Estimate Dev', 'Real']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').replace('None', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Nhận diện cột thời gian
        t_col = 'Start_DT' if 'Start_DT' in df.columns else (next((c for c in df.columns if "start" in c.lower()), df.columns[8]))
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # --- 2. LOGIC CẢNH BÁO LỐ GIỜ ---
        over_est_list = []
        for _, row in df_team.iterrows():
            if 'progress' in row['State_Clean']:
                actual_min = calculate_actual_minutes(row[t_col])
                est_min = float(row['Estimate Dev']) * 60
                # Bắt lỗi 31 phút > 6 phút
                if est_min > 0 and actual_min > est_min:
                    over_est_list.append({
                        "PIC": row['PIC'], "Task": row['Userstory/Todo'], 
                        "Thực tế": f"{int(actual_min)}p", "Dự kiến": f"{int(est_min)}p"
                    })

        st.title("🚀 Sprint Workload Dashboard")

        # Hiển thị Cảnh báo đỏ ngay trên đầu
        if over_est_list:
            st.error(f"🚨 PHÁT HIỆN {len(over_est_list)} TASK VƯỢT GIỜ DỰ KIẾN!")
            st.table(pd.DataFrame(over_est_list))
        else:
            st.success("✅ Mọi task In Progress đều trong tiến độ.")

        # --- 3. THỐNG KÊ ĐẦY ĐỦ PIC (GỒM TASK TỒN ĐỌNG) ---
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            est_sum=('Estimate Dev', 'sum'),
            real_sum=('Real', 'sum')
        ).reset_index()
        # Tính task còn tồn đọng = Tổng - Xong
        pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        st.subheader("👤 Trạng thái theo PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"#### **{row['PIC']}**")
                st.metric("Hoàn thành", f"{row['percent']}%")
                st.write(f"✅ Xong: {int(row['done'])} | 🚧 Đang làm: {int(row['doing'])}")
                st.write(f"⏳ **Tồn đọng: {int(row['pending'])} task**") # Task chưa xong
                st.progress(min(row['percent']/100, 1.0))
                st.divider()

        # Biểu đồ so sánh thời gian (Tính năng cũ)
        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_sum', 'real_sum'], barmode='group', title="Estimate vs Real (h)"), use_container_width=True)

        # --- 4. GỬI DISCORD ---
        st.sidebar.subheader("📢 Discord Report")
        webhook_url = st.sidebar.text_input("Webhook URL:", type="password")
        if st.sidebar.button("📤 Gửi báo cáo"):
            if webhook_url:
                msg = "📊 **SPRINT REPORT**\n"
                for _, r in pic_stats.iterrows():
                    msg += f"👤 **{r['PIC']}**: `{r['percent']}%` (Tồn: {int(r['pending'])})\n"
                if over_est_list:
                    msg += "\n🚨 **CẢNH BÁO LỐ GIỜ:**\n"
                    for item in over_est_list:
                        msg += f"🔥 `{item['PIC']}` lố: {item['Task']} ({item['Thực tế']}/{item['Dự kiến']})\n"
                requests.post(webhook_url, json={"content": msg})
                st.sidebar.success("Đã gửi!")

        st.subheader("📋 Chi tiết danh sách Task")
        st.dataframe(df_team[['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real', t_col]], use_container_width=True)

    else:
        st.error("Không tìm thấy hàng 'Userstory/Todo'.")
except Exception as e:
    st.error(f"Lỗi: {e}")
