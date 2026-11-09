import os
import sys
import csv
import glob
import json
import urllib.parse
import argparse
from dotenv import load_dotenv

load_dotenv()

DEFAULT_AFFILIATE_ID = os.getenv("SHOPEE_AFFILIATE_ID", "15351730428")

def find_feed_file():
    """ค้นหาไฟล์ Product Feed ขนาดยักษ์ในโฟลเดอร์ปัจจุบัน"""
    if os.path.exists("datafeed.csv"):
        return "datafeed.csv"
    feeds = glob.glob("*Product Feed*.csv")
    if feeds:
        return max(feeds, key=os.path.getsize)
    all_csvs = glob.glob("*.csv")
    if all_csvs:
        return max(all_csvs, key=os.path.getsize)
    return None

def build_affiliate_link(product_url, affiliate_id=DEFAULT_AFFILIATE_ID, sub_id="feed_autopost"):
    """สร้างลิงก์ Shopee Affiliate ผ่าน an_redir engine ทางการ"""
    encoded = urllib.parse.quote(product_url.strip(), safe="")
    link = f"https://s.shopee.co.th/an_redir?origin_link={encoded}?&affiliate_id={affiliate_id}"
    if sub_id:
        link += f"&sub_id={sub_id}"
    return link

def import_products_from_feed(limit=200, min_sold=50, min_rating=4.0, category_keyword=None):
    feed_path = find_feed_file()
    if not feed_path:
        print("❌ ไม่พบไฟล์ Product Feed .csv ในโฟลเดอร์นี้")
        return

    print(f"📦 ตรวจพบไฟล์ Feed: {feed_path} (ขนาด {os.path.getsize(feed_path)/(1024*1024):.1f} MB)")
    print(f"🎯 เกณฑ์การคัดเลือกสินค้า: ยอดขาย >= {min_sold} ชิ้น | เรตติ้ง >= {min_rating} ดาว | จำนวนเป้าหมาย = {limit} รายการ")
    if category_keyword:
        print(f"🏷️ หมวดหมู่เป้าหมาย: '{category_keyword}'")

    import db
    db.init_db()
    conn = db.get_db_connection()
    
    # ดึง item_id ที่มีอยู่แล้วเพื่อกันซ้ำ
    existing_ids = set()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT item_id FROM shopee_products")
            for r in cur.fetchall():
                existing_ids.add(str(r[0]))
    except Exception as e:
        print(f"Notice DB: {e}")

    print(f"📊 สินค้าเดิมในฐานข้อมูล: {len(existing_ids):,} รายการ")
    print("⏳ กำลังสแกนไฟล์ Feed เพื่อค้นหาสินค้าขายดีระดับพรีเมียม...")

    imported_items = []
    scanned_lines = 0

    try:
        with open(feed_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            clean_lines = (line.replace('\0', '') for line in f)
            reader = csv.DictReader(clean_lines)

            for row in reader:
                scanned_lines += 1
                if scanned_lines % 50000 == 0:
                    print(f"  ...สแกนไปแล้ว {scanned_lines:,} บรรทัด (พบคัดผ่านเกณฑ์ {len(imported_items)} ชิ้น)")

                itemid = row.get('itemid', '').strip()
                if not itemid or itemid in existing_ids:
                    continue

                # 1. เช็คยอดขาย
                try:
                    sold_val = row.get('item_sold', '0').replace(',', '')
                    sold = int(float(sold_val))
                except:
                    sold = 0
                if sold < min_sold:
                    continue

                # 2. เช็คเรตติ้ง
                try:
                    rating_val = row.get('item_rating', '0')
                    rating = float(rating_val)
                except:
                    rating = 0.0
                if rating < min_rating:
                    continue

                # 3. เช็คหมวดหมู่ (ถ้ามีระบุ)
                cat1 = row.get('global_category1', '')
                cat2 = row.get('global_category2', '')
                cat3 = row.get('global_category3', '')
                all_cats = f"{cat1} {cat2} {cat3}".lower()
                if category_keyword and category_keyword.lower() not in all_cats:
                    continue

                # 4. เช็คราคาและรูปภาพ
                title = row.get('title', '').strip()
                if not title:
                    continue

                price_str = row.get('sale_price') or row.get('price') or '0'
                try:
                    price = float(price_str)
                except:
                    price = 0.0
                if price <= 0:
                    continue

                # รูปภาพหลัก
                image_url = row.get('image_link')
                if not image_url:
                    for k in row:
                        if k.startswith('image_link') and row[k]:
                            image_url = row[k]
                            break
                if not image_url:
                    continue

                # รวมรูปภาพทั้งหมด
                all_imgs = []
                for k in row:
                    if k.startswith('image_link') and row[k]:
                        all_imgs.append(row[k])

                # 5. สร้าง Affiliate Link ด้วย Formula ทางการ
                prod_link = row.get('product_link')
                if not prod_link:
                    shopid = row.get('shopid', '0')
                    prod_link = f"https://shopee.co.th/product/{shopid}/{itemid}"

                aff_link = build_affiliate_link(prod_link, sub_id="feed_autopost")

                # คำนวณคอมมิชชันโดยประมาณ (10% ของราคา)
                commission = round(price * 0.10, 2)
                shop_name = row.get('shop_name') or row.get('seller_name') or 'Shopee Shop'
                desc = row.get('description', '')

                imported_items.append({
                    'item_id': itemid,
                    'title': title,
                    'price': price,
                    'sales': sold,
                    'shop_name': shop_name,
                    'commission_rate': '10%',
                    'commission': commission,
                    'image_url': image_url,
                    'product_link': prod_link,
                    'affiliate_link': aff_link,
                    'description': desc,
                    'rating': rating,
                    'all_images': json.dumps(all_imgs)
                })

                if len(imported_items) >= limit:
                    break

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการอ่านไฟล์ Feed: {e}")

    print(f"\n🎉 สแกนสำเร็จ! พบคัดเลือกสินค้าเข้าเกณฑ์คุณภาพสูง {len(imported_items)} รายการ")
    if not imported_items:
        print("💡 ไม่มีรายการใหม่ที่ตรงตามเกณฑ์ หรือถูกบันทึกไปหมดแล้ว")
        conn.close()
        return

    print("🚀 กำลังบันทึกข้อมูลเข้าสู่ Neon PostgreSQL...")
    saved_count = 0
    try:
        with conn.cursor() as cur:
            for item in imported_items:
                cur.execute("""
                    INSERT INTO shopee_products (
                        item_id, title, price, sales, shop_name, commission_rate, 
                        commission, image_url, product_link, affiliate_link, 
                        description, rating, all_images, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, 
                        %s, %s, %s, NOW()
                    )
                    ON CONFLICT (item_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        price = EXCLUDED.price,
                        sales = EXCLUDED.sales,
                        rating = EXCLUDED.rating,
                        image_url = EXCLUDED.image_url,
                        affiliate_link = EXCLUDED.affiliate_link,
                        description = EXCLUDED.description,
                        all_images = EXCLUDED.all_images
                """, (
                    item['item_id'], item['title'], item['price'], item['sales'], item['shop_name'],
                    item['commission_rate'], item['commission'], item['image_url'], item['product_link'],
                    item['affiliate_link'], item['description'], item['rating'], item['all_images']
                ))
                saved_count += cur.rowcount
            conn.commit()
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

    print(f"✅ บันทึกสินค้าพรีเมียมพร้อมโพสต์สำเร็จ {saved_count} รายการ!")
    print("💡 ตอนนี้คุณสามารถสั่งรัน 'python3 app.py' เพื่อเริ่มโพสต์บทความและโซเชียลได้ทันที!")

def main():
    parser = argparse.ArgumentParser(description="นำเข้าสินค้าขายดีจาก Shopee Datafeed 4GB พร้อมสร้าง Affiliate Link อัตโนมัติ")
    parser.add_argument("--limit", type=int, default=100, help="จำนวนสินค้าที่ต้องการนำเข้า (ค่าเริ่มต้น: 100)")
    parser.add_argument("--min-sold", type=int, default=100, help="ยอดขายขั้นต่ำ (ค่าเริ่มต้น: 100 ชิ้น)")
    parser.add_argument("--min-rating", type=float, default=4.5, help="คะแนนรีวิวขั้นต่ำ (ค่าเริ่มต้น: 4.5 ดาว)")
    parser.add_argument("--category", type=str, default=None, help="กรองเฉพาะหมวดหมู่ เช่น 'food', 'beauty', 'home'")
    args = parser.parse_args()

    import_products_from_feed(
        limit=args.limit,
        min_sold=args.min_sold,
        min_rating=args.min_rating,
        category_keyword=args.category
    )

if __name__ == "__main__":
    main()
