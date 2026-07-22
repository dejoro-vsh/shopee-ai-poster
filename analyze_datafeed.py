import os
import csv
import glob
import json

def analyze():
    # Find CSV files
    csv_files = glob.glob("*.csv")
    if not csv_files:
        print("❌ ไม่พบไฟล์ .csv ในโฟลเดอร์นี้เลยครับ")
        print("💡 กรุณานำไฟล์ datafeed ของคุณมาวางในโฟลเดอร์ shopee-ai-poster และเปลี่ยนชื่อเป็น datafeed.csv ก็ได้ครับ")
        return

    # Prefer datafeed.csv if it exists, else pick the first one
    target_file = "datafeed.csv" if "datafeed.csv" in csv_files else csv_files[0]
    
    print(f"🔍 เริ่มทำการวิเคราะห์ไฟล์: {target_file}")
    print("=" * 50)
    
    try:
        # Try UTF-8 first
        with open(target_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            if not headers:
                print("❌ ไม่พบหัวคอลัมน์ (Headers) ในไฟล์นี้")
                return
                
            print(f"📋 จำนวนคอลัมน์ทั้งหมด: {len(headers)} คอลัมน์")
            print("👉 รายชื่อคอลัมน์:")
            for i, h in enumerate(headers):
                print(f"  {i+1}. {h}")
                
            print("-" * 50)
            
            # Read first 2 rows
            rows = []
            for i, row in enumerate(reader):
                if i >= 2: break
                rows.append(row)
                
            print("📦 ตัวอย่างข้อมูล (2 แถวแรก):")
            for i, row in enumerate(rows):
                print(f"--- แถวที่ {i+1} ---")
                for key, val in row.items():
                    # Truncate long values for readability
                    display_val = str(val)[:100] + "..." if len(str(val)) > 100 else str(val)
                    print(f"  [{key}]: {display_val}")
            
            print("=" * 50)
            print("✅ วิเคราะห์เสร็จสิ้น!")
            print("รบกวนก๊อปปี้ผลลัพธ์ทั้งหมดนี้ ส่งกลับมาในแชทให้ผมดูได้เลยครับ เราจะได้วางแผนประกอบร่างกันต่อ!")
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        print("💡 ไฟล์อาจจะไม่ได้เข้ารหัสแบบ UTF-8 ลองเปิดใน Excel แล้ว Save As เป็น CSV UTF-8 ดูนะครับ")

if __name__ == "__main__":
    analyze()
