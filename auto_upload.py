import os
import glob
import time
import shutil
import csv
import json
import requests
import traceback

DOWNLOADS_PATH = os.path.expanduser('~/Downloads')
API_URL = 'https://shopee-scraper-vercel.vercel.app/api/products'

def parse_price(price_str):
    if not price_str: return 0.0
    cleaned = ''.join(c for c in str(price_str) if c.isdigit() or c == '.')
    try: return float(cleaned) if cleaned else 0.0
    except ValueError: return 0.0

def try_read_csv(file_path):
    encodings_to_try = ['utf-8-sig', 'utf-8', 'utf-16', 'cp874', 'tis-620']
    for enc in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if len(rows) > 0 and len(rows[0].keys()) > 1:
                    print(f"?? ????????????????: {enc} ??????! (?? {len(rows)} ??????)")
                    print(f"?? ???????????????: {list(rows[0].keys())}")
                    return rows
        except Exception as e:
            pass
    print("? ???????? CSV ????????????? (????????????????)")
    return []

def process_csv_and_upload(file_path):
    print(f'\n? ?????????????: {file_path}', flush=True)
    rows = try_read_csv(file_path)
    if not rows:
        return False
        
    products = []
    
    for row in rows:
        # ????????????????????? ???????? Shopee ???????????
        title = row.get('??????????') or row.get('Product Name') or row.get('Item Name') or ''
        affiliateLink = row.get('????????????') or row.get('Affiliate Link') or row.get('????? Affiliate') or ''
        
        if not title or not affiliateLink:
            continue
            
        originalLink = row.get('???????????') or row.get('Product Link') or affiliateLink
        itemid = row.get('??????????') or row.get('Item ID') or None
        sales = row.get('???', '') or row.get('??????', '')
        shopName = row.get('???????????', '') or row.get('Shop Name', '')
        commissionRate = row.get('?????????????????') or row.get('???????????????') or row.get('Commission Rate', '')
        
        commissionStr = row.get('?????????') or row.get('??????????') or row.get('Commission', '0')
        priceStr = row.get('????') or row.get('Price', '0')
        
        if not itemid and originalLink:
            parts = originalLink.split('.')
            if len(parts) > 0: itemid = parts[-1]
                
        products.append({
            'item_id': str(itemid),
            'title': title,
            'price': parse_price(priceStr),
            'sales': str(sales),
            'shop_name': str(shopName),
            'commission_rate': str(commissionRate),
            'commission': parse_price(commissionStr),
            'product_link': str(originalLink),
            'affiliate_link': str(affiliateLink),
            'image_url': None
        })
        
    if not products:
        print('? ????????????????? (???????????????????????????)', flush=True)
        return False
        
    print(f'? ???????? {len(products)} ?????? ?????????????????????????????...', flush=True)
    
    try:
        # To avoid vercel timeout, we can send chunk of 50
        res = requests.post(API_URL, json=products[:50], headers={'Content-Type': 'application/json'}, timeout=20)
        
        if res.status_code in [200, 201]:
            print('?? ??????! ?????????????? Database ?????????', flush=True)
            return True
        else:
            print(f'? ?????????????????????: {res.status_code} {res.text}', flush=True)
            return False
            
    except Exception as e:
        print(f'? ??????????????????????????: {e}', flush=True)
        traceback.print_exc()
        return False

def watch_downloads():
    print('?? ?????????????????? Shopee CSV ?????????? Downloads ???? 24 ??...', flush=True)
    backup_folder = os.path.join(DOWNLOADS_PATH, 'Shopee_Uploaded')
    os.makedirs(backup_folder, exist_ok=True)
    
    while True:
        csv_files = glob.glob(os.path.join(DOWNLOADS_PATH, 'Shopee_*.csv'))
        
        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            
            success = process_csv_and_upload(file_path)
            
            if success:
                try: shutil.move(file_path, os.path.join(backup_folder, file_name))
                except: pass
            else:
                error_folder = os.path.join(DOWNLOADS_PATH, 'Shopee_Error')
                os.makedirs(error_folder, exist_ok=True)
                try: shutil.move(file_path, os.path.join(error_folder, file_name))
                except: pass
                
        time.sleep(10)

if __name__ == '__main__':
    watch_downloads()
