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
                # We will read as simple arrays to bypass ANY header naming/unicode issues!
                reader = csv.reader(f)
                rows = list(reader)
                if len(rows) > 1 and len(rows[0]) > 5:
                    print(f"?? ????????????????: {enc} ??????! (?? {len(rows)} ??????)", flush=True)
                    return rows
        except Exception as e:
            pass
    return []

def clean_str(s):
    if not isinstance(s, str): return s
    return s.strip('\ufeff \t\"\'\n\r')

def process_csv_and_upload(file_path):
    print(f'\n? ?????????????: {file_path}', flush=True)
    rows = try_read_csv(file_path)
    if not rows:
        return False
        
    products = []
    headers = [clean_str(h) for h in rows[0]]
    print(f"?? ??????????: {headers}", flush=True)
    
    # Try to find indexes
    def find_idx(possible_names):
        for i, h in enumerate(headers):
            for p in possible_names:
                if p in h.replace(' ', ''): return i
        return -1
        
    idx_id = find_idx(['??????????', 'ItemID'])
    idx_title = find_idx(['??????????', 'ProductName', 'ItemName'])
    idx_price = find_idx(['????', 'Price'])
    idx_sales = find_idx(['???', '??????'])
    idx_shop = find_idx(['???????????', 'ShopName'])
    idx_comm_rate = find_idx(['?????????????????', '???????????????', 'CommissionRate'])
    idx_comm = find_idx(['?????????', '??????????', 'Commission'])
    idx_link = find_idx(['???????????', 'ProductLink'])
    idx_aff = find_idx(['????????????', 'AffiliateLink'])
    
    # FALLBACK to strict Shopee format if headers are completely unreadable
    if idx_title == -1 or idx_aff == -1:
        print("?? ???????????????????? (???????????) ?????????????????????????????? Shopee ???...", flush=True)
        idx_id = 0
        idx_title = 1
        idx_price = 2
        idx_sales = 3
        idx_shop = 4
        idx_comm_rate = 5
        idx_comm = 6
        idx_link = 7
        idx_aff = 8
        
    for i in range(1, len(rows)):
        row = rows[i]
        if len(row) <= max(idx_title, idx_aff): continue
        
        title = clean_str(row[idx_title])
        affiliateLink = clean_str(row[idx_aff])
        
        if not title or not affiliateLink:
            continue
            
        originalLink = clean_str(row[idx_link]) if idx_link != -1 and len(row) > idx_link else affiliateLink
        itemid = clean_str(row[idx_id]) if idx_id != -1 and len(row) > idx_id else None
        sales = clean_str(row[idx_sales]) if idx_sales != -1 and len(row) > idx_sales else ''
        shopName = clean_str(row[idx_shop]) if idx_shop != -1 and len(row) > idx_shop else ''
        commissionRate = clean_str(row[idx_comm_rate]) if idx_comm_rate != -1 and len(row) > idx_comm_rate else ''
        
        commissionStr = clean_str(row[idx_comm]) if idx_comm != -1 and len(row) > idx_comm else '0'
        priceStr = clean_str(row[idx_price]) if idx_price != -1 and len(row) > idx_price else '0'
        
        if not itemid and originalLink:
            parts = str(originalLink).split('.')
            if len(parts) > 0: itemid = parts[-1]
                
        products.append({
            'item_id': str(itemid),
            'title': str(title),
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
        print('? ????????????????? (??????????????????????????)', flush=True)
        return False
        
    print(f'? ???????? {len(products)} ?????? ?????????????????????????????...', flush=True)
    
    try:
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
