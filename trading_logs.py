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


# Function to get the total quantity of a stock traded
def get_stocks_from_db_under_day_trade_limit():
    now = datetime.now()
    five_days_ago = now - timedelta(days=7)
    cursor.execute('''
    SELECT symbol, COUNT(*) as day_trade_count
    FROM trading_logs
    WHERE timestamp > ?
    AND strftime('%w', timestamp) NOT IN ('0', '6')
    GROUP BY symbol
    HAVING day_trade_count >= 3
    ''', (five_days_ago,))
    return [row[0] for row in cursor.fetchall()]
