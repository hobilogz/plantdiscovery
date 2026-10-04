import os
import psycopg2
from psycopg2.extras import DictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:M93GkYFsj%23qY7hy@db.tbdjkzfvndgwclxfzsoa.supabase.co:5432/postgres")

def get_connection():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS plants (
        id SERIAL PRIMARY KEY,
        scientific_name TEXT NOT NULL UNIQUE,
        common_name_ru TEXT,
        common_name_en TEXT,
        family TEXT,
        genus TEXT,

        description TEXT,
        characteristics TEXT,
        habitat TEXT,
        distribution TEXT,
        flowering_period TEXT,

        toxicity TEXT,
        edibility TEXT,

        interesting_facts TEXT,

        llm_description TEXT,
        llm_features TEXT,
        llm_interesting_fact TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS classification_aliases (
        id SERIAL PRIMARY KEY,
        plant_id INTEGER NOT NULL,
        alias TEXT NOT NULL,

        FOREIGN KEY (plant_id) REFERENCES plants(id)
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        region_name TEXT,
        region_place_id INTEGER,
        game_mode INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_pokedex (
        id SERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        scientific_name TEXT NOT NULL,
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, scientific_name),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS region_cache (
        place_id INTEGER PRIMARY KEY,
        region_name TEXT NOT NULL,
        top_plants_json TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
