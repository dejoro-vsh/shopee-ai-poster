import os
import csv
import glob
from ai import generate_social_content

def find_csv():
    csv_files = glob.glob("*.csv")
    if not csv_files:
        return None
    return csv_files[0]

def parse_price(price_str):
    if not price_str: return 0.0
    cleaned = ''.join(c for c in price_str if c.isdigit() or c == '.')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def test_csv_import():
    csv_file = find_csv()
    if not csv_file:
        print("❌ ไม่พบไฟล์ .csv ในโฟลเดอร์นี้เลยครับ (กรุณาลากไฟล์ CSV มาวางไว้ในโฟลเดอร์ shopee-ai-poster ก่อน)")
        return

    print(f"✅ พบไฟล์ CSV: {csv_file} กำลังอ่านข้อมูล...")
    
    products = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = row.get('ชื่อสินค้า', row.get('Product Name', ''))
            if not title:
                continue
                
            aff_link = row.get('ลิงก์ข้อเสนอ', row.get('Affiliate Link', ''))
            prod_link = row.get('ลิงก์สินค้า', row.get('Product Link', ''))
            item_id = row.get('รหัสสินค้า', row.get('Item ID', ''))
            shop_name = row.get('ชื่อร้านค้า', 'Shopee Shop')
            
            price = parse_price(row.get('ราคา', '0'))
            commission = parse_price(row.get('คอมมิชชัน', row.get('คอมมิชชั่น', '0')))
            
            sales_str = row.get('ขาย', '')
            # Parse sales like "1.2พัน" -> 1200, "500" -> 500
            sales = 0
            if sales_str:
                clean_sales = sales_str.replace(',', '').replace('พัน', '00').replace('.', '')
                try:
                    sales = int(clean_sales)
                except:
                    pass
            
            # Create a dictionary matching what ai.py expects
            products.append({
                'product_id': item_id or str(len(products)),
                'item_name': title,
                'price': price,
                'discount_price': price,
                'commission': commission,
                'category_name': shop_name,
                'aff_link': aff_link,
                'sales': sales,
                'image_url': None
            })

    print(f"🎉 อ่านข้อมูลสำเร็จ! พบสินค้าทั้งหมด {len(products)} ชิ้น")
    
    if len(products) == 0:
        return

    # วิเคราะห์ข้อมูล: เรียงลำดับตามยอดขาย (Sales) จากมากไปน้อย
    products.sort(key=lambda x: x['sales'], reverse=True)

    print("-" * 50)
    print("🤖 กำลังคัดกรองสินค้าที่ 'ขายดีที่สุด' 50 อันดับแรก เพื่อส่งให้ AI วิเคราะห์...")
    
    # Send Top 50 best-selling products to AI
    sample_products = products[:50]
    
    ai_result = generate_social_content(sample_products)
    
    if ai_result:
        print("\n✨ ผลลัพธ์จาก AI (Gemini Flash) ✨")
        print("=======================================")
        print(f"✅ สินค้าที่ AI เลือกโพสต์: {ai_result.get('selected_product_id')}")
        print(f"💡 เหตุผลที่เลือก: {ai_result.get('reason')}")
        print("=======================================")
        print("📱 แคปชั่น Facebook:")
        print(ai_result.get('caption_facebook'))
        print("---------------------------------------")
        print("🐦 แคปชั่น Twitter:")
        print(ai_result.get('caption_twitter'))
        print("---------------------------------------")
        print("💬 แคปชั่น LINE OA:")
        print(ai_result.get('caption_line'))
        print("=======================================")
        print("\n🚀 การทดสอบสำเร็จ! AI สามารถอ่านไฟล์ CSV และแต่งแคปชั่นได้ยอดเยี่ยมมากครับ")
        print("ถ้าคุณพอใจผลลัพธ์นี้ เราสามารถเขียนโค้ดบันทึกสินค้าพวกนี้ลง Database จริงได้เลยครับ!")
    else:
        print("❌ เกิดข้อผิดพลาดในการเรียกใช้ AI")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_csv_import()
