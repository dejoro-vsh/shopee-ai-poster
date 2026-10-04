import os
import glob
import time
import shutil
import csv
import json
import re
import requests

DOWNLOADS_PATH = os.path.expanduser('~/Downloads')
API_URL = 'https://shopee-scraper-vercel.vercel.app/api/products'

def parse_price(price_str):
    if not price_str: return 0.0
    cleaned = ''.join(c for c in str(price_str) if c.isdigit() or c == '.')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def process_csv_and_upload(file_path):
    print(f'? ?????????????: {file_path}')
    products = []
    
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                originalLink = row.get('???????????') or row.get('Product Link') or row.get('????????????') or ''
                affiliateLink = row.get('????????????') or row.get('Affiliate Link') or ''
                title = row.get('??????????') or row.get('Product Name') or ''
                
                if not title or not affiliateLink:
                    continue
                    
                itemid = row.get('??????????') or row.get('Item ID') or None
                productLink = row.get('???????????') or row.get('Product Link') or originalLink
                sales = row.get('???', '')
                shopName = row.get('???????????', '')
                commissionRate = row.get('?????????????????') or row.get('???????????????') or ''
                
                commissionStr = row.get('?????????') or row.get('??????????') or '0'
                commissionAmt = parse_price(commissionStr)
                
                priceStr = row.get('????') or '0'
                priceAmt = parse_price(priceStr)
                
                if not itemid and originalLink:
                    parts = originalLink.split('.')
                    if len(parts) > 0:
                        itemid = parts[-1]
                        
                products.append({
                    'item_id': str(itemid),
                    'title': title,
                    'price': priceAmt,
                    'sales': sales,
                    'shop_name': shopName,
                    'commission_rate': commissionRate,
                    'commission': commissionAmt,
                    'product_link': productLink,
                    'affiliate_link': affiliateLink,
                    'image_url': None
                })
                
        if not products:
            print('? ????????????????????????????????????')
            return False
            
        print(f'? ???????? {len(products)} ?????? ?????????????????????????????...')
        
        # To match the extension's behavior: slice(0, 10) to avoid overloading or test
        # test_products = products[:10]
        # Or we send all of them if the server can handle it. We will send all.
        
        res = requests.post(API_URL, json=products, headers={'Content-Type': 'application/json'})
        
        if res.status_code in [200, 201]:
            print('?? ??????! ??????????????????????? Database ?????????')
            return True
        else:
            print(f'? ?????????????????????: {res.text}')
            return False
            
    except Exception as e:
        print(f'? ???????????????????????????: {e}')
        return False

def watch_downloads():
    print('?? ?????????????????? Shopee CSV ?????????? Downloads ???? 24 ??...')
    backup_folder = os.path.join(DOWNLOADS_PATH, 'Shopee_Uploaded')
    os.makedirs(backup_folder, exist_ok=True)
    
    while True:
        csv_files = glob.glob(os.path.join(DOWNLOADS_PATH, 'Shopee_*.csv'))
        
        for file_path in csv_files:
            file_name = os.path.basename(file_path)
            print(f'\n?? ??????????: {file_name}')
            
            success = process_csv_and_upload(file_path)
            
            if success:
                try:
                    shutil.move(file_path, os.path.join(backup_folder, file_name))
                    print(f'??? ???????? {file_name} ????????????? Shopee_Uploaded ????')
                except Exception as e:
                    print(f'?? ????????????????????: {e}')
            else:
                # If failed, move to an error folder so it doesn't loop infinitely
                error_folder = os.path.join(DOWNLOADS_PATH, 'Shopee_Error')
                os.makedirs(error_folder, exist_ok=True)
                try:
                    shutil.move(file_path, os.path.join(error_folder, file_name))
                except: pass
                
        time.sleep(10)

if __name__ == '__main__':
    watch_downloads()
