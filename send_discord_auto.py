import requests
import pandas as pd
import os
import gspread
import json

# Cấu hình ID Discord (Thay thế số ID thực tế của bạn vào đây)
DISCORD_TAGS = {
    'TEAM_ROLE': '<@&1387617307190366329>' # ID của nhóm/role
}

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
SHEET_URL = os.environ.get("GSHEETS_URL")
SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT")

def get_report():
    try:
        # 1. Xác thực và kết nối
        creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(SHEET_URL)
        worksheet = sh.get_worksheet(0)
        data = worksheet.get_all_values()
        
        # 2. Xử lý DataFrame
        df_full = pd.DataFrame(data)
        header_idx = df_full[df_full.eq("Userstory/Todo").any(axis=1)].index[0]
        df = pd.DataFrame(data[header_idx + 1:], columns=data[header_idx])
        
        # 3. Chuẩn hóa dữ liệu (Xóa khoảng trắng, chuyển chữ thường)
        df.columns = [str(c).strip() for c in df.columns]
        df['State_Clean'] = df['State'].fillna('none').str.strip().str.lower()
        df['State_Clean'] = df['State_Clean'].replace(['', None], 'none')
        
        valid_pics = ['Tài', 'Dương', 'QA', 'Quân', 'Phú', 'Thịnh', 'Đô', 'Thành', 'Anim', 'Thắng VFX']
        df_team = df[df['PIC'].isin(valid_pics)].copy()

        # 4. TÍNH TOÁN (Đảm bảo kết quả là số)
        # Done_List bao gồm cả 'done' và 'cancel'
        pic_stats = df_team.groupby('PIC').agg(
            total=('Userstory/Todo', 'count'),
            done=('State_Clean', lambda x: x.isin(['done', 'cancel']).sum()),
            ip=('State_Clean', lambda x: (x == 'in progress').sum()),
            none=('State_Clean', lambda x: (x == 'none').sum())
        ).reset_index()

        # 5. SOẠN TIN NHẮN
        PIC_EMOJIS = {
        "QA": "🔍", "Tài": "💰", "Dương": "🌊", "Quân": "⚔️", "Phú": "🏦",
        "Thịnh": "📈", "Đô": "🏰", "Thành": "🏰", "Anim": "🎬",
        "Thắng VFX": "🎆"
        }


        
        msg = f"📊 **CẬP NHẬT TIẾN ĐỘ SPRINT** {DISCORD_TAGS.get('TEAM_ROLE', '@everyone')}\n"
        msg += "--------------------------\n"
        
        for _, r in pic_stats.iterrows():
            # Ép kiểu dữ liệu về số nguyên để hiển thị đúng
            total = int(r['total'])
            done = int(r['done'])
            ip = int(r['ip'])
            none = int(r['none'])
            
            progress = (done / total * 100) if total > 0 else 0
            icon = "🟢" if progress >= 80 else "🟡" if progress >= 50 else "🔴"
            
            mention = DISCORD_TAGS.get(r['PIC'], f"**{r['PIC']}**")
            
            # Dòng hiển thị Done quan trọng ở đây:
            msg += f"{icon} \n"
            msg += f"{emoji} {mention}: `{progress:.1f}%` hoàn thành\n"
            msg += f" ┣ ✅ **Xong/Cancel: `{done}`**\n"
            msg += f" ┣ 🚧 Đang làm: `{ip}`\n"
            msg += f" ┗ ⏳ Chưa làm: `{none}`\n"
            msg += "──────────────────\n"
        
        msg += "💡 *Ghi chú: Task được cập nhật hàng ngày theo Sprint backlog.*"

        # 6. Gửi tới Discord
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": msg})
            print("✅ Đã gửi báo cáo thành công với đầy đủ số task Done.")

    except Exception as e:
        print(f"❌ Lỗi xử lý: {e}")

if __name__ == "__main__":
    get_report()
