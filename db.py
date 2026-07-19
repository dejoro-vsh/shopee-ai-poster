import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date

def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL is not set in .env")
    return psycopg2.connect(db_url)

def get_todays_products(limit=50):
    """Fetches the latest products added today, ordered by highest commission"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            today = date.today()
            query = """
                SELECT 
                    id, item_id as product_id, title as item_name, price, price as discount_price, 
                    commission, image_url, affiliate_link as aff_link, shop_name as category_name
                FROM shopee_products
                WHERE DATE(created_at) = %s
                ORDER BY commission DESC
                LIMIT %s
            """
            cur.execute(query, (today, limit))
            products = cur.fetchall()
            return products
    finally:
        conn.close()

def init_db():
    """Initializes the database schema if it doesn't exist"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS posted_history (
                    product_id VARCHAR(255) PRIMARY KEY,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    finally:
        conn.close()

def get_posted_product_ids():
    """Returns a set of all product IDs that have already been posted"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT product_id FROM posted_history")
            # Return as a set for O(1) lookups
            return {row[0] for row in cur.fetchall()}
    finally:
        conn.close()

def mark_as_posted(product_id):
    """Saves a product ID to the posted history"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO posted_history (product_id) VALUES (%s) ON CONFLICT (product_id) DO NOTHING",
                (product_id,)
            )
            conn.commit()
    finally:
        conn.close()
