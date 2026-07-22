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
    
    print(f"📖 กำลังอ่านข้อมูลจาก {csv_file}...")
    
    updates = []
    try:
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row.get('itemid', '').strip()
                if not item_id:
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
                    
                # Description
                description = row.get('description', '')
                
                # Collect all images
                all_images = []
                for key in row.keys():
                    if key and key.startswith('image_link') and row[key]:
                        all_images.append(row[key])
                
                # Select the first image as the main image if available
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

    print(f"🔄 กำลังอัปเดตข้อมูลเข้า Database (จำนวน {len(updates)} รายการ)...")
    
    conn = db.get_db_connection()
    updated_count = 0
    try:
        with conn.cursor() as cur:
            for item in updates:
                # Update the row if item_id matches. 
                # We also update image_url just in case it was missing.
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
        
    print(f"✅ อัปเดตข้อมูลสำเร็จ! สินค้าใน Database ได้รับการอัปเกรดข้อมูลแล้ว {updated_count} รายการ")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    enrich_database()
