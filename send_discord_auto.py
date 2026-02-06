import requests
import pandas as pd
import os

# Lấy Secrets từ GitHub (Đảm bảo bạn đã đổi Webhook mới như hướng dẫn trước)
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
SHEET_URL = os.environ.get("GSHEETS_URL")

def get_report():
    try:
        # Chuyển link Sheet sang dạng export CSV để đọc trực tiếp
        # Link của bạn: https://docs.google.com/spreadsheets/d/1llUlTDfR413oZelu-AoMsC0lEzHqXOkB4SCwc_4zmAo/edit...
        csv_url = SHEET_URL.split('/edit')[0] + '/export?format=csv&gid=982443592'
        
        # Đọc dữ liệu
        df_all = pd.read_csv(csv_url, header=None)
        # Tìm hàng có chứa tiêu đề 'Userstory/Todo'
        header_idx = df_all[df_all.eq("Userstory/Todo").any(axis=1)].index[0]
        df = pd.read_csv(csv_url, skiprows=header_idx + 1)
        
        # Chuẩn hóa dữ liệu
        df.columns = [str(c).strip() for c in df.columns]
        df['State_Clean'] = df['State'].fillna('None').replace('', 'None').str.strip().str.lower()
        
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Tùng', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # Tính toán (Cancel = Done)
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            ip=('State_Clean', lambda x: (x == 'in progress').sum()),
            none=('State_Clean', lambda x: (x == 'none').sum())
        ).reset_index()

        # Soạn tin nhắn
        msg = "⏰ **BÁO CÁO TỰ ĐỘNG (8:30 AM)** ☀️\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        for _, r in pic_stats.iterrows():
            p = (r['done'] / r['total'] * 100) if r['total'] > 0 else 0
            icon = "🟢" if p >= 80 else "🟡"
            msg += f"{icon} **{r['PIC']}**: `{p:.1f}%` | Xong: `{int(r['done'])}` | IP: `{int(r['ip'])}` | None: `{int(r['none'])}` \n"
        
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📊 *Cancel được tính là Done theo yêu cầu.*"

        # Gửi Discord
        if WEBHOOK_URL:
            res = requests.post(WEBHOOK_URL, json={"content": msg})
            print(f"Status: {res.status_code}")
        else:
            print("Lỗi: Không tìm thấy DISCORD_WEBHOOK trong Secrets.")

    except Exception as e:
        print(f"Lỗi xử lý dữ liệu: {e}")

if __name__ == "__main__":
    get_report() # Đã sửa thành get_report() để khớp với định nghĩa hàm bên trên
