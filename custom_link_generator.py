import os
import sys
import re
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "https://shopee-scraper-vercel.vercel.app/api/products")
AFFILIATE_CUSTOM_LINK_URL = "https://affiliate.shopee.co.th/offer/custom_link"

def extract_ids_from_url(url):
    """แยก item_id และ shop_id จาก URL ของ Shopee"""
    item_id, shop_id = None, None
    
    # แบบ /product/shop_id/item_id
    m1 = re.search(r'product/(\d+)/(\d+)', url)
    if m1:
        shop_id, item_id = m1.group(1), m1.group(2)
        return item_id, shop_id

    # แบบ -i.shop_id.item_id
    m2 = re.search(r'-i\.(\d+)\.(\d+)', url)
    if m2:
        shop_id, item_id = m2.group(1), m2.group(2)
        return item_id, shop_id
        
    # แบบ itemKeys=item_id.xxx.&shopId=shop_id (จากตะกร้า/cart)
    m3 = re.search(r'itemKeys=(\d+).*shopId=(\d+)', url)
    if m3:
        item_id, shop_id = m3.group(1), m3.group(2)
        return item_id, shop_id

    return None, None

def convert_via_playwright(product_url, headless=False):
    """
    แปลงลิงก์สินค้าธรรมดาเป็น Shopee Affiliate Link โดยรันผ่าน Browser บนเครื่อง Mac
    เพื่อผ่านระบบ Anti-Bot (Datadome/SAP) 100%
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ ไม่พบไลบรารี playwright กรุณาติดตั้งด้วยคำสั่ง: pip install playwright && playwright install chromium")
        return None

    print(f"🚀 กำลังเชื่อมต่อเบราว์เซอร์เพื่อแปลงลิงก์: {product_url}")
    
    with sync_playwright() as p:
        # วิธีที่ 1: ตรวจสอบว่ามี Chrome รันด้วย Remote Debugging Port 9222 อยู่หรือไม่
        browser = None
        context = None
        is_cdp = False
        
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            is_cdp = True
            print("⚡ เชื่อมต่อกับ Google Chrome (Port 9222) ที่เปิดอยู่บน Mac สำเร็จ!")
        except Exception:
            # วิธีที่ 2: ถ้าไม่ได้เปิด port 9222 ให้เปิด Chromium ด้วย Session Profile ของผู้ใช้
            user_data_dir = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")
            if not os.path.exists(user_data_dir):
                user_data_dir = os.path.expanduser("~/.shopee_browser_profile")
                
            print("🌐 เปิดเบราว์เซอร์สำหรับส่งคำขอไปยัง Shopee Affiliate...")
            context = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome" if sys.platform == "darwin" else None,
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
        page = context.new_page() if is_cdp else context.pages[0] if context.pages else context.new_page()
        
        try:
            # ไปที่หน้า Custom Link
            if AFFILIATE_CUSTOM_LINK_URL not in page.url:
                page.goto(AFFILIATE_CUSTOM_LINK_URL, wait_until="networkidle", timeout=30000)
                time.sleep(2)
                
            # ตรวจสอบว่าล็อกอินอยู่หรือไม่
            if "login" in page.url:
                print("⚠️ คุณยังไม่ได้ล็อกอินในระบบ Shopee Affiliate")
                print("👉 กรุณาล็อกอินในหน้าต่างเบราว์เซอร์ที่เปิดขึ้นมา แล้วรันสคริปต์ใหม่อีกครั้ง")
                if not headless:
                    time.sleep(15)
                return None

            print("📡 กำลังส่งคำสั่ง batchCustomLink ภายในเบราว์เซอร์...")
            
            # เรียกใช้ GraphQL ภายใน Browser Context โดยตรง
            js_code = f"""
            async () => {{
                const targetUrl = "{product_url}";
                const csrfMatch = document.cookie.match(/csrftoken=([^;]+)/);
                const csrfToken = csrfMatch ? csrfMatch[1] : "";
                
                const payload = {{
                    operationName: "batchGetCustomLink",
                    query: `
                        query batchGetCustomLink($linkParams: [CustomLinkParam!], $sourceCaller: SourceCaller){{
                            batchCustomLink(linkParams: $linkParams, sourceCaller: $sourceCaller){{
                                shortLink
                                longLink
                                failCode
                            }}
                        }}
                    `,
                    variables: {{
                        linkParams: [{{
                            originalLink: targetUrl,
                            advancedLinkParams: {{}}
                        }}],
                        sourceCaller: "CUSTOM_LINK_CALLER"
                    }}
                }};
                
                const response = await fetch("https://affiliate.shopee.co.th/api/v3/gql?q=batchCustomLink", {{
                    method: "POST",
                    headers: {{
                        "content-type": "application/json; charset=UTF-8",
                        "csrf-token": csrfToken
                    }},
                    body: JSON.stringify(payload)
                }});
                
                const json = await response.json();
                return json;
            }}
            """
            
            result = page.evaluate(js_code)
            
            # แกะ shortLink ออกมาจาก Response
            batch_list = result.get("data", {}).get("batchCustomLink", [])
            if batch_list and len(batch_list) > 0:
                short_link = batch_list[0].get("shortLink")
                if short_link:
                    print(f"🎉 สร้างลิงก์สำเร็จ: {short_link}")
                    return short_link
                    
            print(f"⚠️ ผลลัพธ์จาก Shopee ไม่พบลิงก์ย่อ: {result}")
            
            # Fallback: ใช้ UI บนหน้าเว็บ พิมพ์ลงใน Textarea แล้วคลิกปุ่ม
            print("🔄 ลองใช้ UI อัตโนมัติ (พิมพ์ลงกล่องข้อความ)...")
            textarea = page.locator("textarea")
            if textarea.count() > 0:
                textarea.first.fill(product_url)
                time.sleep(0.5)
                # คลิกปุ่ม เอา ลิงก์
                submit_btn = page.locator("button:has-text('เอา ลิงก์'), button:has-text('รับลิงก์'), button:has-text('Get Link')")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    time.sleep(2)
                    
                    # ค้นหาลิงก์ s.shopee.co.th ในหน้าเว็บ
                    content = page.content()
                    found_links = re.findall(r'https://s\.shopee\.co\.th/[a-zA-Z0-9]+', content)
                    if found_links:
                        short_link = found_links[0]
                        print(f"🎉 สร้างลิงก์สำเร็จจาก UI: {short_link}")
                        return short_link

        except Exception as e:
            print(f"❌ เกิดข้อผิดพลาดระหว่างรันบนเบราว์เซอร์: {e}")
        finally:
            if not is_cdp:
                context.close()
                
    return None

def lookup_product_details(item_id):
    """ค้นหาข้อมูลสินค้า (ชื่อ, รูป, ราคา) จาก Datafeed หรือฐานข้อมูล"""
    # 1. ค้นหาจาก Database ก่อน
    try:
        from db import get_db_connection
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT title, price, image_url, description FROM shopee_products WHERE item_id = %s", (str(item_id),))
            row = cur.fetchone()
            if row and row[0]:
                conn.close()
                return {
                    "title": row[0],
                    "price": float(row[1]) if row[1] else 0.0,
                    "image_url": row[2],
                    "description": row[3] or ""
                }
        conn.close()
    except Exception:
        pass

    # 2. ค้นหาจาก datafeed.csv ในเครื่อง
    import glob
    import csv
    csv_files = glob.glob("*.csv")
    target_csv = "datafeed.csv" if "datafeed.csv" in csv_files else (csv_files[0] if csv_files else None)
    
    if target_csv and os.path.exists(target_csv):
        print(f"📖 กำลังค้นหาข้อมูลสินค้า ID {item_id} ใน {target_csv}...")
        try:
            with open(target_csv, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('itemid', '').strip() == str(item_id):
                        return {
                            "title": row.get('item_name', ''),
                            "price": float(row.get('price', 0)),
                            "image_url": row.get('image', ''),
                            "description": row.get('item_description', '')
                        }
        except Exception as e:
            print(f"⚠️ ไม่สามารถอ่าน Datafeed ได้: {e}")

    return {
        "title": f"สินค้า Shopee รหัส {item_id}",
        "price": 0.0,
        "image_url": None,
        "description": ""
    }

def save_to_database(product_data):
    """ส่งข้อมูลสินค้าเข้าสู่ Vercel API / Neon DB"""
    try:
        res = requests.post(
            API_URL, 
            json=[product_data], 
            headers={"Content-Type": "application/json"},
            timeout=20
        )
        if res.status_code in [200, 201]:
            print("✅ บันทึกสินค้าลง Database สำเร็จ! พร้อมสำหรับให้ AI นำไปโพสต์")
            return True
        else:
            print(f"❌ บันทึก Database ไม่สำเร็จ: {res.status_code} {res.text}")
            return False
    except Exception as e:
        print(f"❌ Network Error เมื่อเชื่อมต่อ Database: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("📌 วิธีใช้งาน:")
        print("  python3 custom_link_generator.py \"<URL สินค้า Shopee>\"")
        print("\nตัวอย่าง:")
        print("  python3 custom_link_generator.py \"https://shopee.co.th/product/163965007/19629049057\"")
        return

    product_url = sys.argv[1].strip()
    item_id, shop_id = extract_ids_from_url(product_url)
    print(f"🔍 ตรวจพบ Item ID: {item_id}, Shop ID: {shop_id}")

    # 1. แปลงลิงก์ผ่าน Playwright
    short_link = convert_via_playwright(product_url)
    if not short_link:
        print("❌ ไม่สามารถสร้างลิงก์ Affiliate ได้ กรุณาตรวจสอบว่าล็อกอิน Shopee Affiliate บน Chrome หรือยัง")
        return

    # 2. ค้นหารูปภาพและรายละเอียดสินค้า
    details = lookup_product_details(item_id) if item_id else {}
    
    product_payload = {
        "item_id": str(item_id) if item_id else str(int(time.time())),
        "title": details.get("title") or f"สินค้า Shopee แนะนำ",
        "price": details.get("price") or 0.0,
        "sales": "100+",
        "shop_name": "Shopee Mall",
        "commission_rate": "10%",
        "commission": 50.0,
        "product_link": product_url,
        "affiliate_link": short_link,
        "image_url": details.get("image_url")
    }

    # 3. บันทึกเข้า Database
    save_to_database(product_payload)

if __name__ == "__main__":
    main()
