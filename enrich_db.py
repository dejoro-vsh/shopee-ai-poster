import os
import csv
import glob
import json
import db

def find_csv():
    csv_files = glob.glob("*.csv")
    if not csv_files:
        return None
    return "datafeed.csv" if "datafeed.csv" in csv_files else csv_files[0]

def enrich_database():
    csv_file = find_csv()
    if not csv_file:
        print("❌ ไม่พบไฟล์ .csv ในโฟลเดอร์นี้")
        return

    print("🔧 กำลังอัปเกรดโครงสร้าง Database...")
    db.init_db()
    
    conn = db.get_db_connection()
    target_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT item_id FROM shopee_products WHERE item_id IS NOT NULL")
            for row in cur.fetchall():
                target_ids.add(str(row[0]))
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
        
    if not target_ids:
        print("⚠️ ไม่พบข้อมูลสินค้าเก่าใน Database เลยครับ (ไม่มีรายการให้ไปประกอบร่าง)")
        return
        
    print(f"🎯 มีสินค้าเป้าหมายใน Database ทั้งหมด {len(target_ids)} ชิ้น")
    print(f"📖 กำลังอ่านข้อมูลจากไฟล์ {csv_file} (อาจใช้เวลาสักครู่สำหรับไฟล์ 1 ล้านบรรทัด)...")
    
    updates = []
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            clean_lines = (line.replace('\0', '') for line in f)
            reader = csv.DictReader(clean_lines)
            
            for i, row in enumerate(reader):
                if i > 0 and i % 100000 == 0:
                    print(f"  ...อ่านไปแล้ว {i:,} บรรทัด (พบข้อมูลตรงกัน {len(updates)} ชิ้น)")
                    
                item_id = row.get('itemid', '').strip()
                if not item_id or item_id not in target_ids:
                    continue
                
                # Parse sales
                sales_str = row.get('item_sold', '0')
                sales = 0
                try:
                    sales = int(sales_str.replace(',', ''))
                except:
                    pass
                
                # Parse rating
                rating_str = row.get('item_rating', '0')
                rating = 0.0
                try:
                    rating = float(rating_str)
                except:
                    pass
                    
                description = row.get('description', '')
                
                all_images = []
                for key in row.keys():
                    if key and key.startswith('image_link') and row[key]:
                        all_images.append(row[key])
                
                main_image = all_images[0] if all_images else None
                
                updates.append({
                    'item_id': item_id,
                    'description': description,
                    'sales': sales,
                    'rating': rating,
                    'all_images': json.dumps(all_images),
                    'main_image': main_image
                })
                
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์ CSV: {e}")
        return

    print(f"🔄 อ่านครบ 1 ล้านบรรทัดแล้ว! สรุปเจอสินค้าที่ตรงกัน {len(updates)} รายการ")
    if not updates:
        print("✅ ไม่มีอะไรต้องอัปเดตครับ")
        return
        
    print("🚀 กำลังอัปเดตข้อมูลเข้า Database...")
    
    updated_count = 0
    try:
        with conn.cursor() as cur:
            for item in updates:
                cur.execute("""
                    UPDATE shopee_products 
                    SET description = %s,
                        sales = %s,
                        rating = %s,
                        all_images = %s,
                        image_url = COALESCE(image_url, %s)
                    WHERE item_id = %s
                """, (
                    item['description'],
                    item['sales'],
                    item['rating'],
                    item['all_images'],
                    item['main_image'],
                    item['item_id']
                ))
                if cur.rowcount > 0:
                    updated_count += cur.rowcount
            conn.commit()
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()
        
    print(f"✅ อัปเดตข้อมูลสำเร็จ! ประกอบร่างข้อมูลเสร็จสิ้น {updated_count} รายการ")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    enrich_database()
