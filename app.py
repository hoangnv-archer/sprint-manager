import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta

# --- 1. CỐ ĐỊNH MÚI GIỜ VIỆT NAM ---
VN_TZ = timezone(timedelta(hours=7))

def get_actual_hours(start_val):
    if pd.isna(start_val) or str(start_val).strip().lower() in ['none', '', 'nat']:
        return 0
    try:
        start_dt = pd.to_datetime(start_val)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=VN_TZ)
        now_vn = datetime.now(VN_TZ)
        diff = now_vn - start_dt
        return diff.total_seconds() / 3600 
    except:
        return 0

# --- 2. CẤU HÌNH CÁC DỰ ÁN ---
PROJECTS = {
    "Sprint Team 2 (Dự án 1)": {
        "url": "https://docs.google.com/spreadsheets/d/1hentY_r7GNVwJWM3wLT7LsA3PrXQidWnYahkfSwR9Kw/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Chuân', 'Việt', 'Thắng', 'QA', 'Mai', 'Hải Anh', 'Thuật', 'Hiếu'],
        "platform": "Telegram",
        "bot_token": "8535993887:AAFDNSLk9KRny99kQrAoQRbgpKJx_uHbkpw",
        "chat_id": "-1002102856307",
        "topic_id": 18251
    },
    "Sprint Dashboard Final (Dự án mới)": {
        "url": "https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit?pli=1&gid=982443592#gid=982443592",
        "pics": ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX'],
        "platform": "Discord"
    }
}

st.set_page_config(page_title="Multi-Project Sprint Dashboard", layout="wide")

# --- 3. SIDEBAR CHỌN DỰ ÁN ---
st.sidebar.title("📁 Quản lý dự án")
selected_p = st.sidebar.selectbox("Chọn dự án muốn xem:", list(PROJECTS.keys()))
config = PROJECTS[selected_p]

# --- 4. KẾT NỐI VÀ XỬ LÝ DỮ LIỆU ---
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
                df[col] = df[col].astype(str).str.replace(',', '.').replace('None', '0')
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # CỘT THỜI GIAN
        t_col = next((c for c in df.columns if "start" in c.lower()), None)
        df['State_Clean'] = df['State'].fillna('None').str.strip().str.lower()
        df_team = df[df['PIC'].isin(config['pics'])].copy()

        # LOGIC CẢNH BÁO LỐ GIỜ
        over_est_list = []
        if t_col:
            for _, row in df_team.iterrows():
                if 'progress' in row['State_Clean']:
                    actual_h = get_actual_hours(row[t_col])
                    est_h = float(row['Estimate Dev'])
                    if est_h > 0 and actual_h > est_h:
                        over_est_list.append({
                            "PIC": row['PIC'], 
                            "Task": row['Userstory/Todo'], 
                            "Thực tế": f"{round(actual_h * 60)}p", 
                            "Dự kiến": f"{round(est_h * 60)}p"
                        })

        st.title(f"🚀 {selected_p}")

        # Hiển thị bảng cảnh báo
        if over_est_list:
            st.error(f"🚨 PHÁT HIỆN {len(over_est_list)} TASK LÀM QUÁ GIỜ DỰ KIẾN!")
            st.table(pd.DataFrame(over_est_list))

        # THỐNG KÊ PIC
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel', 'dev done']).sum()),
            doing=('State_Clean', lambda x: x.str.contains('progress').sum()),
            est_total=('Estimate Dev', 'sum'),
            real_total=('Real', 'sum')
        ).reset_index()
        
        pic_stats['pending'] = pic_stats['total'] - pic_stats['done']
        pic_stats['percent'] = (pic_stats['done'] / pic_stats['total'] * 100).fillna(0).round(1)

        # Hiển thị Metric
        st.subheader("👤 Trạng thái chi tiết từng PIC")
        cols = st.columns(5)
        for i, row in pic_stats.iterrows():
            with cols[i % 5]:
                st.markdown(f"#### **{row['PIC']}**")
                st.metric("Tiến độ", f"{row['percent']}%")
                st.write(f"✅ Xong: {int(row['done'])} | 🚧 Đang: {int(row['doing'])}")
                st.write(f"⏳ **Tồn: {int(row['pending'])} task**")
                st.progress(min(row['percent']/100, 1.0))
                st.divider()

        st.plotly_chart(px.bar(pic_stats, x='PIC', y=['est_total', 'real_total'], barmode='group'), use_container_width=True)

        # --- 5. GỬI BÁO CÁO (DISCORD HOẶC TELEGRAM) ---
        st.sidebar.divider()
        st.sidebar.subheader(f"📢 Gửi qua {config['platform']}")
        
        if config['platform'] == "Discord":
            webhook_url = st.sidebar.text_input("Webhook URL Dự án mới:", type="password")
            if st.sidebar.button("📤 Gửi báo cáo Discord"):
                if webhook_url:
                    msg = f"📊 **REPORT: {selected_p}**\n"
                    for _, r in pic_stats.iterrows():
                        msg += f"👤 **{r['PIC']}**: `{r['percent']}%` (Tồn: {int(r['pending'])})\n"
                    if over_est_list:
                        msg += "\n🚨 **LỐ GIỜ:** " + ", ".join([f"{i['PIC']}({i['Thực tế']})" for i in over_est_list])
                    requests.post(webhook_url, json={"content": msg})
                    st.sidebar.success("Đã gửi Discord!")
        
        else: # Telegram cho Team 2
            if st.sidebar.button("📤 Gửi báo cáo Telegram"):
                msg = f"<b>📊 REPORT: {selected_p}</b>\n"
                for _, r in pic_stats.iterrows():
                    msg += f"• {r['PIC']}: <b>{r['percent']}%</b> (Tồn: {int(r['pending'])})\n"
                
                url_tg = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
                payload = {
                    "chat_id": config['chat_id'], 
                    "message_thread_id": config['topic_id'],
                    "text": msg, "parse_mode": "HTML"
                }
                requests.post(url_tg, json=payload)
                st.sidebar.success("Đã gửi Telegram!")

        # Bảng chi tiết
        st.subheader("📋 Bảng chi tiết Task")
        show_cols = ['Userstory/Todo', 'State', 'PIC', 'Estimate Dev', 'Real']
        if t_col: show_cols.append(t_col)
        st.dataframe(df_team[show_cols], use_container_width=True)

    else:
        st.error("Lỗi: Không tìm thấy hàng tiêu đề 'Userstory/Todo' trong Sheet này.")
except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
