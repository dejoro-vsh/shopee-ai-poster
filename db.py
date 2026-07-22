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
                WITH top_comm AS (
                    SELECT id, item_id as product_id, title as item_name, price, price as discount_price, 
                           commission, image_url, affiliate_link as aff_link, shop_name as category_name,
                           description, sales, rating, all_images
                    FROM shopee_products
                    WHERE DATE(created_at) = %s
                    ORDER BY commission DESC
                    LIMIT 20
                ),
                cheapest AS (
                    SELECT id, item_id as product_id, title as item_name, price, price as discount_price, 
                           commission, image_url, affiliate_link as aff_link, shop_name as category_name,
                           description, sales, rating, all_images
                    FROM shopee_products
                    WHERE DATE(created_at) = %s
                    ORDER BY price ASC
                    LIMIT 15
                ),
                random_items AS (
                    SELECT id, item_id as product_id, title as item_name, price, price as discount_price, 
                           commission, image_url, affiliate_link as aff_link, shop_name as category_name,
                           description, sales, rating, all_images
                    FROM shopee_products
                    WHERE DATE(created_at) = %s
                    ORDER BY RANDOM()
                    LIMIT 15
                )
                SELECT * FROM top_comm
                UNION
                SELECT * FROM cheapest
                UNION
                SELECT * FROM random_items
            """
            # We pass the 'today' parameter 3 times for the 3 CTEs
            cur.execute(query, (today, today, today))
            products = cur.fetchall()
            return products
    finally:
        conn.close()

def init_db():
    """Initializes the database schema if it doesn't exist"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create posted_history
            cur.execute("""
                CREATE TABLE IF NOT EXISTS posted_history (
                    product_id VARCHAR(255) PRIMARY KEY,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Create shopee_products if it doesn't exist (basic schema)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shopee_products (
                    id SERIAL PRIMARY KEY,
                    item_id VARCHAR(255) UNIQUE,
                    title TEXT,
                    price DECIMAL(10,2),
                    commission DECIMAL(10,2),
                    image_url TEXT,
                    affiliate_link TEXT,
                    shop_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Alter table to add rich data columns if they don't exist
            alter_statements = [
                "ALTER TABLE shopee_products ADD COLUMN IF NOT EXISTS description TEXT;",
                "ALTER TABLE shopee_products ADD COLUMN IF NOT EXISTS sales INTEGER DEFAULT 0;",
                "ALTER TABLE shopee_products ADD COLUMN IF NOT EXISTS rating FLOAT DEFAULT 0.0;",
                "ALTER TABLE shopee_products ADD COLUMN IF NOT EXISTS all_images JSONB;"
            ]
            for stmt in alter_statements:
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print(f"Notice: {e}")
            
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
