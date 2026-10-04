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
                    print(f"?? ????????????????: {enc} ??????! (?? {len(rows)} ??????)", flush=True)
                    return rows
        except Exception as e:
            pass
    return []

def clean_str(s):
    if not isinstance(s, str): return s
    return s.strip('\ufeff \t\"\'\n\r')

def find_val(row_dict, possible_keys):
    for k, v in row_dict.items():
        if k is None: continue
        clean_k = clean_str(k).replace(' ', '')
        for pk in possible_keys:
            if pk.replace(' ', '') in clean_k:
                return clean_str(v)
    return ''

def process_csv_and_upload(file_path):
    print(f'\n? ?????????????: {file_path}', flush=True)
    rows = try_read_csv(file_path)
    if not rows:
        return False
        
    products = []
    
    # Strip whitespace, BOM, and quotes from keys and values
    cleaned_rows = []
    for r in rows:
        cleaned_rows.append({clean_str(k): clean_str(v) for k, v in r.items() if k is not None})
        
    print(f"?? ????????????????????: {cleaned_rows[0]}", flush=True)
        
    for row in cleaned_rows:
        title = find_val(row, ['??????????', 'ProductName', 'ItemName'])
        affiliateLink = find_val(row, ['????????????', 'AffiliateLink'])
        
        if not title or not affiliateLink:
            continue
            
        originalLink = find_val(row, ['???????????', 'ProductLink']) or affiliateLink
        itemid = find_val(row, ['??????????', 'ItemID']) or None
        sales = find_val(row, ['???', '??????'])
        shopName = find_val(row, ['???????????', 'ShopName'])
        commissionRate = find_val(row, ['?????????????????', '???????????????', 'CommissionRate'])
        
        commissionStr = find_val(row, ['?????????', '??????????', 'Commission']) or '0'
        priceStr = find_val(row, ['????', 'Price']) or '0'
        
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
        print('? ????????????????? (??????????????? ??????????????)', flush=True)
        return False
        
    print(f'? ???????? {len(products)} ?????? ?????????????????????????????...', flush=True)
    
    try:
        res = requests.post(API_URL, json=products, headers={'Content-Type': 'application/json'}, timeout=20)
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
