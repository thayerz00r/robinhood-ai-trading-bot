from datetime import datetime, timedelta
import sqlite3

# Initialize database connection
conn = sqlite3.connect('trading_logs.db')
cursor = conn.cursor()


# Create table for trading logs
cursor.execute('''
CREATE TABLE IF NOT EXISTS trading_logs (
    id INTEGER PRIMARY KEY,
    symbol TEXT,
    decision TEXT,
    quantity INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()


# Function to log trades to the database
def log_trade_to_db(symbol, decision, quantity):
    cursor.execute('''
    INSERT INTO trading_logs (symbol, decision, quantity)
    VALUES (?, ?, ?)
    ''', (symbol, decision, quantity))
    conn.commit()
