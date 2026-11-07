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

# Cookie สำรองจาก session ของผู้ใช้ (ใช้ล็อกอินอัตโนมัติ)
DEFAULT_COOKIE = os.getenv("SHOPEE_COOKIE", """_ga=GA1.1.1696941576.1781497662; _QPWSDCXHZQA=ba001511-081d-4c83-a344-4482ef71e191; REC7iLP4Q=801fe792-9ae3-4cf8-b866-32d9a440b996; _fbp=fb.2.1781497663196.763263184191975582; language=th; SPC_F=RgDbKNlpiOgVr8LU66eT1squtJ0LS0qb; REC_T_ID=90028a18-6872-11f1-80a8-1ec99a30c062; SPC_CLIENTID=UmdEYktObHBpT2dWtwarojeufgglhjrl; SC_DFP=VKMdJQoxVCpfKcFcupojiIwdMonyaxyl; SPC_EC=-; _ga_DSXZBPJ4D3=GS2.1.s1784364553$o3$g0$t1784364553$j60$l0$h0; _gcl_au=1.1.22812299.1789312335; language=th; csrftoken=s9PiQdbaN5JZbawNi5IazkwYnBQVhOf8; _sapid=abfeaa97948185fdaea366951b432fb1ab4ce7802c25d7a2676943fc; SPC_SI=aGCRagAAAAA4cDFld3hJeLrBpwgAAAAAVFo0T29laEs=; SPC_ST=H4Oh28RpTTED/t5xsmVWUm7fpKDMO48ir4BDgXh6HRP6LS8JNcmjD1JrLxARGDhV0cBN+Yt60/uZn09lo0hpwLLgkqMH0hwr+qz6F4A8cETfNTLR/2HXnB6z2yKudlCziTbhbc9nsqcS362x38oKwbdMNkwHoctVCOMzjhpcYSH6Jpj9NAeYxbmEET/HWXnSOQa/jrtmurgBzSUmcpzIkA==.AMpr1yLVF/uyfbwRPbCBXDwqSb3T8De9WIE8aa/Sk6I9; SPC_U=12773835173; SPC_R_T_ID=jzb8kLn9F/Jzp/rJmFo37Cd2JcqBC8TgGTtDAJSdx/tGkFllFVYy2YvUncZJQsRZJgP2o4pwFvyLqmZttN6qx50GFfX6xVd9Rlyw1inYsPvwYOdVvPl/gIR2pUqD7GdWqYwigQ3rOSHFV/z8srfjbM0B4b0qLInwhcZilAuCZs8=; SPC_R_T_IV=eGMyYXdpbTRMZzhFOW53bQ==; SPC_T_ID=jzb8kLn9F/Jzp/rJmFo37Cd2JcqBC8TgGTtDAJSdx/tGkFllFVYy2YvUncZJQsRZJgP2o4pwFvyLqmZttN6qx50GFfX6xVd9Rlyw1inYsPvwYOdVvPl/gIR2pUqD7GdWqYwigQ3rOSHFV/z8srfjbM0B4b0qLInwhcZilAuCZs8=; SPC_T_IV=eGMyYXdpbTRMZzhFOW53bQ==; ds=b7ffa71ca69729f1376bc8ec0ad09c4b;""")

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

def parse_cookies(cookie_string):
    """แปลง cookie string เป็น list of dicts สำหรับ Playwright"""
    cookies = []
    for item in cookie_string.split(';'):
        item = item.strip()
        if '=' in item:
            name, val = item.split('=', 1)
            cookies.append({
                'name': name.strip(),
                'value': val.strip(),
                'domain': '.shopee.co.th',
                'path': '/'
            })
    return cookies

def convert_via_playwright(product_url, headless=False):
    """
    แปลงลิงก์สินค้าธรรมดาเป็น Shopee Affiliate Link โดยรันผ่าน Browser Context
    แก้ปัญหา SingletonLock และแก้ปัญหา Timeout 30000ms อย่างถาวร
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ ไม่พบไลบรารี playwright กรุณาติดตั้งด้วยคำสั่ง: pip3 install playwright && playwright install chromium")
        return None

    print(f"🚀 กำลังเชื่อมต่อเบราว์เซอร์เพื่อแปลงลิงก์: {product_url}")
    
    with sync_playwright() as p:
        browser = None
        context = None
        is_cdp = False
        
        # 1. ลองเชื่อมต่อ Chrome Port 9222 ที่เปิดอยู่ก่อน (เร็วสุด 0.5 วินาที)
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9222", timeout=3000)
            context = browser.contexts[0]
            is_cdp = True
            print("⚡ เชื่อมต่อกับ Google Chrome (Port 9222) สำเร็จ!")
        except Exception:
            # 2. ถ้าไม่ได้เปิด Port 9222 ให้เปิด Browser อิสระในโฟลเดอร์เฉพาะ (ไม่ชนกับ Google Chrome ที่เปิดอยู่)
            session_dir = os.path.expanduser("~/.shopee_poster_session")
            os.makedirs(session_dir, exist_ok=True)
            print("🌐 เปิดเบราว์เซอร์สำหรับส่งคำขอไปยัง Shopee Affiliate...")
            
            context = p.chromium.launch_persistent_context(
                user_data_dir=session_dir,
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            
            # ฉีด Cookie ล็อกอินเข้าไปอัตโนมัติ เพื่อไม่ต้องล็อกอินใหม่ทุกครั้ง
            if DEFAULT_COOKIE:
                try:
                    cookies = parse_cookies(DEFAULT_COOKIE)
                    context.add_cookies(cookies)
                    print("🔑 ฉีด Cookie ล็อกอินเข้าสู่ระบบเรียบร้อย")
                except Exception as e:
                    print(f"Notice: {e}")
            
        page = context.new_page() if is_cdp else context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(20000)
        
        try:
            # เปิดหน้า Custom Link (ใช้ domcontentloaded แทน networkidle ป้องกัน Timeout)
            print("⏳ กำลังเปิดหน้าสร้างลิงก์ Shopee...")
            page.goto(AFFILIATE_CUSTOM_LINK_URL, wait_until="domcontentloaded", timeout=20000)
            time.sleep(2)
            
            # ตรวจสอบสถานะการล็อกอิน
            if "login" in page.url:
                print("⚠️ ยังไม่ได้ล็อกอินในระบบ Shopee Affiliate")
                print("👉 กรุณาล็อกอินบนหน้าต่างเบราว์เซอร์ที่เปิดขึ้นมา (มีเวลารอ 60 วินาที)...")
                try:
                    # รอจนกว่าผู้ใช้จะล็อกอินเสร็จและกลับมาหน้า offer/custom_link
                    page.wait_for_url("**/offer/**", timeout=60000)
                    print("🎉 ตรวจพบการล็อกอินสำเร็จ!")
                except Exception:
                    print("❌ หมดเวลาล็อกอิน กรุณารันใหม่อีกครั้ง")
                    return None

            print("📡 กำลังส่งคำสั่ง batchCustomLink ภายในเบราว์เซอร์...")
            
            # รัน GraphQL ในหน้าต่างเบราว์เซอร์โดยตรง (ผ่าน Anti-bot 100%)
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
                
                return await response.json();
            }}
            """
            
            result = page.evaluate(js_code)
            
            # แกะ shortLink ออกมาจาก Response
            batch_list = result.get("data", {}).get("batchCustomLink", [])
            if batch_list and len(batch_list) > 0:
                short_link = batch_list[0].get("shortLink")
                if short_link:
                    print(f"🎉 สร้างลิงก์ Affiliate สำเร็จ: {short_link}")
                    return short_link
                    
            print(f"⚠️ ผลลัพธ์ API ภายใน: {result}")
            
            # แผนสำรอง: สั่งพิมพ์ลงกล่อง Textarea แล้วกดปุ่ม "เอา ลิงก์"
            print("🔄 ลองใช้ UI สำรองบนหน้าเว็บ...")
            textarea = page.locator("textarea")
            if textarea.count() > 0:
                textarea.first.fill(product_url)
                time.sleep(0.5)
                submit_btn = page.locator("button:has-text('เอา ลิงก์'), button:has-text('รับลิงก์'), button:has-text('Get Link')")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    time.sleep(3)
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
                try:
                    context.close()
                except Exception:
                    pass
                
    return None

def lookup_product_details(item_id):
    """ค้นหาข้อมูลสินค้า (ชื่อ, รูป, ราคา) จาก Database หรือ Datafeed 4GB"""
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
        "title": f"สินค้า Shopee แนะนำ (รหัส {item_id})",
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
            print("✅ บันทึกสินค้าลง Database เรียบร้อยแล้ว!")
            print(f"   ↳ ชื่อสินค้า: {product_data.get('title')}")
            print(f"   ↳ ลิงก์ Affiliate: {product_data.get('affiliate_link')}")
            print(f"   ↳ รูปภาพ: {'มีรูป ✅' if product_data.get('image_url') else 'ไม่มีรูป ❌'}")
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
        print("  python3 custom_link_generator.py \"https://shopee.co.th/cart?itemKeys=19629049057.181503016088.&shopId=163965007\"")
        return

    product_url = sys.argv[1].strip()
    item_id, shop_id = extract_ids_from_url(product_url)
    print(f"🔍 ตรวจพบ Item ID: {item_id}, Shop ID: {shop_id}")

    # 1. แปลงลิงก์ผ่าน Playwright Browser
    short_link = convert_via_playwright(product_url)
    if not short_link:
        print("❌ ไม่สามารถสร้างลิงก์ Affiliate ได้")
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
