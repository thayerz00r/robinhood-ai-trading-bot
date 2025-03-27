import robin_stocks.robinhood as rh
import time
from pytz import timezone
import pandas as pd

import mfa
from log import *
from config import MODE, ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD
from config import OP_SERVICE_ACCOUNT_NAME, OP_SERVICE_ACCOUNT_TOKEN, OP_VAULT_NAME, OP_ITEM_NAME


# Main login function that orchestrates the login process
async def login_to_robinhood():
    try:
        # Try to get MFA code from secret first
        mfa_code = mfa.get_from_secret()

        # If no MFA secret, try 1Password
        if not mfa_code and OP_SERVICE_ACCOUNT_NAME and OP_SERVICE_ACCOUNT_TOKEN and OP_VAULT_NAME and OP_ITEM_NAME:
            mfa_code = await mfa.get_from_1password()

        try:
            if mfa_code:
                log_debug("Attempting to login to Robinhood with MFA...")
                login_resp = rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, mfa_code=mfa_code)
                log_debug("Robinhood login successful with MFA.")
            else:
                log_debug("Attempting to login to Robinhood without MFA...")
                login_resp = rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)
                log_debug("Robinhood login successful without MFA.")
            if not login_resp:
                raise Exception("Login failed - no response received")
            return login_resp
        except Exception as e:
            log_error(f"Failed to login to Robinhood: {e}")
            return None

    except Exception as e:
        log_error(f"An error occurred during Robinhood login: {e}")
        return None


# Run a Robinhood function with retries and delay between attempts (to handle rate limits)
def rh_run_with_retries(func, *args, max_retries=3, delay=60, **kwargs):
    for attempt in range(max_retries):
        result = func(*args, **kwargs)
        msg = f"Function: {func.__name__}, Parameters: {args}, Attempt: {attempt + 1}/{max_retries}, Result: {result}"
        msg = msg[:1000] + '...' if len(msg) > 1000 else msg
        log_debug(msg)
        if result is not None:
            return result
        log_debug(f"Function: {func.__name__}, Parameters: {args}, Retrying in {delay} seconds...")
        time.sleep(delay)
    return None


# Check if the market is open
def is_market_open():
    eastern = timezone('US/Eastern')
    now = datetime.now(eastern)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close


# Round money
def round_money(price, decimals=2):
    if price is None:
        return None
    return round(float(price), decimals)


# Round quantity
def round_quantity(quantity, decimals=6):
    if quantity is None:
        return None
    return round(float(quantity), decimals)


# Extract data from my stocks
def extract_my_stocks_data(stock_data):
    return {
        "current_price": round_money(stock_data['price']),
        "my_quantity": round_quantity(stock_data['quantity']),
        "my_average_buy_price": round_money(stock_data['average_buy_price']),
    }


# Extract data from watchlist stocks
def extract_watchlist_data(stock_data):
    return {
        "current_price": round_money(stock_data['price']),
        "my_quantity": round_quantity(0),
        "my_average_buy_price": round_money(0),
    }


# Extract sell response data
def extract_sell_response_data(sell_resp):
    return {
        "quantity": round_quantity(sell_resp['quantity']),
        "price": round_money(sell_resp['price']),
    }


# Extract buy response data
def extract_buy_response_data(buy_resp):
    return {
        "quantity": round_quantity(buy_resp['quantity']),
        "price": round_money(buy_resp['price']),
    }


# Enrich stock data with Relative strength index (RSI)
def enrich_with_rsi(stock_data, historical_data, symbol):
    if len(historical_data) < 14:
        log_debug(f"Not enough data to calculate RSI for {symbol}")
        return stock_data

    prices = [round_money(day['close_price']) for day in historical_data]
    delta = pd.Series(prices).diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean().iloc[-1]
    avg_loss = loss.rolling(window=14).mean().iloc[-1]
    if avg_loss == 0:
        rs = 100
    else:
        rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    stock_data["rsi"] = round(float(rsi), 2)
    return stock_data


# Enrich stock data with Volume-weighted average price (VWAP)
def enrich_with_vwap(stock_data, historical_data, symbol):
    if len(historical_data) < 1:
        log_debug(f"Not enough data to calculate VWAP for {symbol}")
        return stock_data

    stock_history_df = pd.DataFrame(historical_data)
    stock_history_df["close_price"] = pd.to_numeric(stock_history_df["close_price"], errors="coerce")
    stock_history_df["high_price"] = pd.to_numeric(stock_history_df["high_price"], errors="coerce")
    stock_history_df["low_price"] = pd.to_numeric(stock_history_df["low_price"], errors="coerce")
    stock_history_df["volume"] = pd.to_numeric(stock_history_df["volume"], errors="coerce")

    # Drop rows where volume is zero or NaN
    stock_history_df = stock_history_df[stock_history_df["volume"] > 0]

    # Compute the Typical Price
    stock_history_df["typical_price"] = (stock_history_df["high_price"] + stock_history_df["low_price"] + stock_history_df["close_price"]) / 3

    # Compute VWAP
    sum_of_volumes = stock_history_df["volume"].sum()
    dot_product = stock_history_df["volume"].dot(stock_history_df["typical_price"])

    if sum_of_volumes == 0:  # Prevent division by zero
        log_debug(f"Total volume is zero for {symbol}, cannot compute VWAP")
        return stock_data

    vwap = dot_product / sum_of_volumes
    stock_data["vwap"] = round_money(vwap)

    return stock_data


# Enrich stock data with Moving average (MA)
def enrich_with_moving_averages(stock_data, historical_data, symbol):
    if len(historical_data) < 200:
        log_debug(f"Not enough data to calculate moving averages for {symbol}")
        return stock_data

    prices = [round_money(day['close_price']) for day in historical_data]
    moving_avg_50 = pd.Series(prices).rolling(window=50).mean().iloc[-1]
    moving_avg_200 = pd.Series(prices).rolling(window=200).mean().iloc[-1]
    stock_data["50_day_mavg_price"] = round_money(moving_avg_50)
    stock_data["200_day_mavg_price"] = round_money(moving_avg_200)
    return stock_data


# Get analyst ratings for a stock by symbol
def enrich_with_analyst_ratings(stock_data, ratings_data, symbol):
    stock_data["analyst_summary"] = ratings_data['summary']
    stock_data["analyst_ratings"] = list(map(lambda rating: {
        "published_at": rating['published_at'],
        "type": rating['type'],
        "text": rating['text'].decode('utf-8'),
    }, ratings_data['ratings']))
    return stock_data


# Get my buying power and account info
def get_account_info():
    resp = rh_run_with_retries(rh.profiles.load_account_profile)
    if resp is None:
        raise Exception("Error getting profile data: No response")

    margin_balances = resp.get('margin_balances', {})
    day_trade_buying_power = float(margin_balances.get('day_trade_buying_power', 0))
    day_trade_ratio = float(margin_balances.get('day_trade_ratio', 0))
    day_trades_protection = margin_balances.get('day_trades_protection', False)
    is_pdt_forever = margin_balances.get('is_pdt_forever', False)
    marked_pattern_day_trader_date = margin_balances.get('marked_pattern_day_trader_date')
    pattern_day_trader_expiry_date = margin_balances.get('pattern_day_trader_expiry_date')

    # Account is PDT restricted if:
    # 1. It's permanently marked as PDT
    # 2. It has PDT protection enabled and no day trade buying power
    # 3. It's marked as PDT and hasn't expired yet
    is_pdt_restricted = (
        is_pdt_forever or
        (day_trades_protection and day_trade_buying_power <= 0) or
        (marked_pattern_day_trader_date and not pattern_day_trader_expiry_date)
    )

    return {
        "buying_power": round_money(resp['buying_power']),
        "day_trade_buying_power": round_money(day_trade_buying_power),
        "day_trade_ratio": day_trade_ratio,
        "is_pdt_restricted": is_pdt_restricted,
        "pdt_status": {
            "is_forever": is_pdt_forever,
            "marked_date": marked_pattern_day_trader_date,
            "expiry_date": pattern_day_trader_expiry_date,
            "protection_enabled": day_trades_protection
        }
    }


# Get portfolio stocks
def get_portfolio_stocks():
    resp = rh_run_with_retries(rh.build_holdings)
    if resp is None:
        raise Exception("Error getting portfolio stocks: No response")
    return resp


# Get watchlist stocks by name
def get_watchlist_stocks(name):
    resp = rh_run_with_retries(rh.get_watchlist_by_name, name)
    if resp is None or 'results' not in resp:
        raise Exception(f"Error getting watchlist {name}: No response")
    return resp['results']


# Get analyst ratings for a stock by symbol
def get_ratings(symbol):
    resp = rh_run_with_retries(rh.stocks.get_ratings, symbol)
    if resp is None:
        raise Exception(f"Error getting ratings for {symbol}: No response")
    return resp


# Get historical stock data by symbol
def get_historical_data(symbol, interval="day", span="year"):
    resp = rh_run_with_retries(rh.stocks.get_stock_historicals, symbol, interval=interval, span=span)
    if resp is None:
        raise Exception(f"Error getting historical data for {symbol}: No response")
    return resp


# Sell a stock by symbol and quantity
def sell_stock(symbol, quantity):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm sell for {symbol} of {quantity}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    sell_resp = rh_run_with_retries(rh.orders.order_sell_market, symbol, quantity, timeInForce="gfd")
    if sell_resp is None:
        raise Exception(f"Error selling {symbol}: No response")
    return sell_resp


# Buy a stock by symbol and quantity
def buy_stock(symbol, quantity):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm buy for {symbol} of {quantity}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    buy_resp = rh_run_with_retries(rh.orders.order_buy_market, symbol, quantity, timeInForce="gfd")
    if buy_resp is None:
        raise Exception(f"Error buying {symbol}: No response")
    return buy_resp

