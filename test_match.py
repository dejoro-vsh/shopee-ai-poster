import os
import csv
import glob
import db
import random

def find_csv():
    csv_files = glob.glob("*.csv")
    if not csv_files:
        return None
    return "datafeed.csv" if "datafeed.csv" in csv_files else csv_files[0]

def test_match():
    print("🔍 กำลังดึงตัวอย่างสินค้า 20 รายการจาก Database...")
    conn = db.get_db_connection()
    sample_items = []
    try:
        with conn.cursor() as cur:
            # ดึงสินค้าแบบสุ่มมา 20 ตัว
            cur.execute("SELECT item_id, title FROM shopee_products WHERE item_id IS NOT NULL ORDER BY RANDOM() LIMIT 20")
            for row in cur.fetchall():
                sample_items.append({"item_id": str(row[0]), "title": row[1]})
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    finally:
        conn.close()

    if not sample_items:
        print("❌ ไม่พบสินค้าใน Database")
        return

    csv_file = find_csv()
    if not csv_file:
        print("❌ ไม่พบไฟล์ .csv")
        return

    print(f"📖 กำลังสแกนหาในไฟล์ {csv_file} ว่ามี 20 ตัวนี้ไหม...")
    
    # เก็บ itemid จากไฟล์ CSV ทั้งหมดไว้ใน memory (เฉพาะ itemid) เพื่อให้ค้นหาได้ไวขึ้น
    csv_item_ids = set()
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            clean_lines = (line.replace('\0', '') for line in f)
            reader = csv.DictReader(clean_lines)
            for row in reader:
                item_id = row.get('itemid', '').strip()
                if item_id:
                    csv_item_ids.add(item_id)
    except Exception as e:
        print(f"❌ อ่านไฟล์ CSV พลาด: {e}")
        return

    print("=" * 60)
    print("📊 ผลการทดสอบ 20 สินค้า (จาก Database VS Datafeed)")
    print("=" * 60)
    
    found_count = 0
    for item in sample_items:
        db_id = item['item_id']
        title = item['title'][:40] + "..." if len(item['title']) > 40 else item['title']
        
        if db_id in csv_item_ids:
            found_count += 1
            print(f"✅ [เจอใน Datafeed] ID: {db_id} | {title}")
        else:
            print(f"❌ [ไม่เจอ] ID: {db_id} | {title}")
            
    print("=" * 60)
    print(f"สรุป: เจอ {found_count} ชิ้น จากทั้งหมด 20 ชิ้น (คิดเป็น {found_count/20*100}%)")
    print("=" * 60)
    print("💡 สังเกตชื่อสินค้าที่ไม่เจอครับ ส่วนใหญ่จะเป็นสินค้าแบบไหน? (เช่น ร้านไทย, ของกินโลคอล) ซึ่งมันมักจะไม่อยู่ในไฟล์ Global ครับ")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_match()
