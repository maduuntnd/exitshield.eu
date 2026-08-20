import sqlite3
from contextlib import contextmanager
import os
from pathlib import Path

# Database path
DATABASE_PATH = os.getenv("DATABASE_URL", "sqlite:///./exitshield.db").replace("sqlite:///", "")

# Ensure database directory exists
db_dir = Path(DATABASE_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize the database with required tables."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            stripe_customer_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stripe_subscription_id TEXT UNIQUE,
            status TEXT NOT NULL,
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create exit_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exit_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            feedback TEXT,
            offer_applied TEXT,
            churned BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create index on stripe_customer_id for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id 
        ON users(stripe_customer_id)
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized at {DATABASE_PATH}")


@contextmanager
def get_db():
    """
    Get a database connection with proper cleanup.
    
    IMPORTANT: Uses try/finally to ensure connection is always closed,
    even if an exception occurs during the yield.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    finally:
        if conn:
            conn.close()  # Always close the connection
