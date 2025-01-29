import robin_stocks.robinhood as rh
import time
from pytz import timezone
import pandas as pd
from onepassword import *

from log import *
import pyotp
import sys
from config import MODE, ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, ROBINHOOD_MFA_SECRET
from config import OP_SERVICE_ACCOUNT_NAME, OP_SERVICE_ACCOUNT_TOKEN, OP_VAULT_NAME, OP_ITEM_NAME


async def login_to_robinhood():
    try:
        mfa_code = ""
        if ROBINHOOD_MFA_SECRET:
            mfa_code = pyotp.TOTP(ROBINHOOD_MFA_SECRET).now()
            log_debug(f"Generated MFA code based on MFA secret: {mfa_code}")
        elif OP_SERVICE_ACCOUNT_NAME and OP_SERVICE_ACCOUNT_TOKEN and OP_VAULT_NAME and OP_ITEM_NAME:
            log_debug("Attempting to login to 1Password to get MFA code...")
            onePasswordClient = await Client.authenticate(
                auth=OP_SERVICE_ACCOUNT_TOKEN,
                integration_name=OP_SERVICE_ACCOUNT_NAME,
                integration_version="v1.0.0",
            )
            mfa_code = await onePasswordClient.secrets.resolve("op://" + OP_VAULT_NAME + "/" + OP_ITEM_NAME + "/one-time password?attribute=otp")

        if mfa_code:
            log_debug("Attempting to login to Robinhood with MFA...")
            rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD, mfa_code=mfa_code)
            log_debug("Robinhood login successful with MFA.")
        else:
            log_debug("Attempting to login to Robinhood without MFA...")
            rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)
            log_debug("Robinhood login successful without MFA.")

    except Exception as e:
        log_error(f"An error occurred during Robinhood login: {e}")
        sys.exit(1)


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


# Calculate moving averages for stock prices
def calculate_moving_averages(prices, short_window=50, long_window=200):
    short_mavg = pd.Series(prices).rolling(window=short_window).mean().iloc[-1]
    long_mavg = pd.Series(prices).rolling(window=long_window).mean().iloc[-1]
    return short_mavg, long_mavg


# Extract data from my stocks
def extract_my_stocks_data(stock_data):
    return {
        "price": round_money(stock_data['price']),
        "quantity": round_quantity(stock_data['quantity']),
        "average_buy_price": round_money(stock_data['average_buy_price']),
    }


# Extract data from watchlist stocks
def extract_watchlist_data(stock_data):
    return {
        "price": round_money(stock_data['price']),
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


# Enrich stock data with moving averages
def enrich_with_moving_averages(stock_data, symbol):
    prices = get_historical_data(symbol)
    if len(prices) >= 200:
        moving_avg_50, moving_avg_200 = calculate_moving_averages(prices)
        stock_data["50_day_mavg_price"] = round_money(moving_avg_50)
        stock_data["200_day_mavg_price"] = round_money(moving_avg_200)
    return stock_data


# Get analyst ratings for a stock by symbol
def enrich_with_analyst_ratings(stock_data, symbol):
    ratings = get_ratings(symbol)
    if 'ratings' in ratings and len(ratings['ratings']) > 0:
        last_sell_rating = next((rating for rating in ratings['ratings'] if rating['type'] == "sell"), None)
        last_buy_rating = next((rating for rating in ratings['ratings'] if rating['type'] == "buy"), None)
        if last_sell_rating:
            stock_data["analyst_sell_opinion"] = last_sell_rating['text'].decode('utf-8')
        if last_buy_rating:
            stock_data["analyst_buy_opinion"] = last_buy_rating['text'].decode('utf-8')
    if 'summary' in ratings and ratings['summary']:
        summary = ratings['summary']
        total_ratings = sum([summary['num_buy_ratings'], summary['num_hold_ratings'], summary['num_sell_ratings']])
        if total_ratings > 0:
            buy_percent = summary['num_buy_ratings'] / total_ratings * 100
            sell_percent = summary['num_sell_ratings'] / total_ratings * 100
            hold_percent = summary['num_hold_ratings'] / total_ratings * 100
            stock_data["analyst_summary_distribution"] = f"sell: {sell_percent:.0f}%, buy: {buy_percent:.0f}%, hold: {hold_percent:.0f}%"
    return stock_data


# Get my buying power
def get_buying_power():
    resp = rh_run_with_retries(rh.profiles.load_account_profile)
    if resp is None or 'buying_power' not in resp:
        raise Exception("Error getting profile data: No response")
    return round_money(resp['buying_power'])


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
    return [round_money(day['close_price']) for day in resp]


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
