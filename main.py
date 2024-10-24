from openai import OpenAI
import robin_stocks.robinhood as rh
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Global variables
# OpenAI API key
OPENAI_API_KEY = "..." 
# Robinhood username is the email address used for login
ROBINHOOD_USERNAME = "..."
# Robinhood password is not the same as the login password
ROBINHOOD_PASSWORD = "..."
# Watchlist names to get stocks from
WATCHLIST_NAMES = ["My List"]
# Default percentage of buying power that will be used for buying stocks, for example if buying power is 1000$ and BUYING_AMOUNT_PERCENTAGE = 0.25, then 250$ will be used for buying stocks
BUYING_AMOUNT_PERCENTAGE = 0.25
# Minimum amount to buy in dollars
MIN_BUYING_AMOUNT_USD = 0.02
# Maximum amount to buy in dollars
MAX_BUYING_AMOUNT_USD = 50
# Default percentage of holding that will be sold at once, for example if holding is 100 stocks and SELLING_AMOUNT_PERCENTAGE = 0.25, then 25 stocks will be sold at once
SELLING_AMOUNT_PERCENTAGE = 0.25
# Interval for running the bot, in seconds
BOT_RUN_INTERVAL_SECONDS = 60

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Print with timestamp
def print_with_timestamp(msg):
    print(f"[{datetime.now()}]  {msg}")

# Login to Robinhood
def login_to_robinhood():
    rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)

# Get historical stock prices for calculating moving averages
def get_historical_data(stock_symbol, interval="day", span="year"):
    """
    Fetch historical data for a stock. 
    Interval can be 'day', 'hour', etc., and span can be 'week', 'month', 'year'.
    """
    historical_data = rh.stocks.get_stock_historicals(stock_symbol, interval=interval, span=span)
    # Extract closing prices and timestamps
    prices = [float(day['close_price']) for day in historical_data]
    return prices

# Calculate the moving averages for given prices
def calculate_moving_averages(prices, short_window=50, long_window=200):
    """
    Calculate the short (50-day) and long (200-day) moving averages.
    """
    short_mavg = pd.Series(prices).rolling(window=short_window).mean().iloc[-1]
    long_mavg = pd.Series(prices).rolling(window=long_window).mean().iloc[-1]
    return short_mavg, long_mavg

# Buy stocks
def buy_stock(stock_symbol, amount):
    quote = rh.stocks.get_latest_price(stock_symbol)
    price = float(quote[0])
    quantity = round(amount / price, 6)
    # return rh.orders.order_buy_fractional_by_price(stock_symbol, amount)
    return rh.orders.order_buy_fractional_by_quantity(stock_symbol, quantity)

# Sell stocks
def sell_stock(stock_symbol, quantity):
    return rh.orders.order_sell_fractional_by_quantity(stock_symbol, quantity)

# Make decision to buy or sell based on moving averages
def make_decision(stock_symbol):
    simple_avg_decision = "hold"
    openai_decision = "hold"
    final_decision = "hold"

    # Get historical data
    prices = get_historical_data(stock_symbol)
    if len(prices) < 200:
        raise Exception("Not enough data to calculate moving averages")
    
    # Calculate moving averages
    moving_avg_50, moving_avg_200 = calculate_moving_averages(prices, short_window=50, long_window=200)

    # Simple decision based on moving averages
    if moving_avg_50 > moving_avg_200:
        simple_avg_decision = "buy"
    elif moving_avg_50 < moving_avg_200:
        simple_avg_decision = "sell"
    else:
        simple_avg_decision = "hold"

    final_decision = simple_avg_decision

    # Query OpenAI for a concise decision
    prompt = (
        f"Given that the 50-day moving average is {moving_avg_50} "
        f"and the 200-day moving average is {moving_avg_200}, "
        "please return only one action word: buy, sell, or hold."
    )

    # Query OpenAI for insight
    chat_completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert stock trading advisor."},
            {"role": "user", "content": prompt}
        ]
    )
    openai_decision = chat_completion.choices[0].message.content.strip().lower()
    openai_decision = openai_decision[:-1] if openai_decision[-1] == '.' else openai_decision

    if openai_decision in ["buy", "sell", "hold"]:
        final_decision = openai_decision
    
    return simple_avg_decision, openai_decision, final_decision

# Get your portfolio and buying power
def get_buying_power():
    profile_data = rh.profiles.load_account_profile()
    buying_power = float(profile_data['buying_power'])
    return buying_power

# Get available stocks in your portfolio
def get_my_stocks():
    return rh.build_holdings()

# Get stocks from a watch list
def get_watch_list_stocks(name):
    resp = rh.get_watchlist_by_name(name)
    return resp['results']

# Main trading loop
def trading_bot():
    login_to_robinhood()
    
    while True:
        try:
            print_with_timestamp("=====================================")

            bought_list = []
            sold_list = []

            # Process my stocks
            my_stocks = get_my_stocks()         
            print_with_timestamp(f"My stocks > {len(my_stocks)}")  

            # Make decision for each stock
            for stock_symbol in my_stocks:
                try:                    
                    simple_avg_decision, openai_decision, final_decision = make_decision(stock_symbol)
                    print_with_timestamp(f"{stock_symbol} > Decision: {final_decision} (Simple: {simple_avg_decision}, OpenAI: {openai_decision})")
                    
                    if final_decision == "buy":
                        buying_power = get_buying_power()
                        amount = round(buying_power * BUYING_AMOUNT_PERCENTAGE, 6)
                        amount = min(amount, MAX_BUYING_AMOUNT_USD)
                        amount = max(amount, MIN_BUYING_AMOUNT_USD)
                        amount = min(amount, buying_power)
                        buy_resp = buy_stock(stock_symbol, amount)
                        if 'id' in buy_resp:
                            bought_list.append(stock_symbol)
                            print_with_timestamp(f"{stock_symbol} > Bought {amount}$")
                        else:
                            print_with_timestamp(f"{stock_symbol} > Error buying {amount}$: {buy_resp}")
                    elif final_decision == "sell":
                        quantity = round(float(my_stocks[stock_symbol]['quantity']) * SELLING_AMOUNT_PERCENTAGE, 6)
                        sell_resp = sell_stock(stock_symbol, quantity)
                        if 'id' in sell_resp:
                            sold_list.append(stock_symbol)
                            print_with_timestamp(f"{stock_symbol} > Sold {quantity} shares")
                        else:
                            print_with_timestamp(f"{stock_symbol} > Error selling {quantity} shares: {sell_resp}")
                    else:
                        print_with_timestamp(f"{stock_symbol} > Hold: based on decision")
                except Exception as e:
                    print_with_timestamp(f"{stock_symbol} > Error processing: {e}")
            
            for watchlist_name in WATCHLIST_NAMES:
                # Process watchlist stocks
                watchlist_stocks = get_watch_list_stocks(watchlist_name)
                print_with_timestamp(f"{watchlist_name} watchlist stocks > {len(watchlist_stocks)}")

                # Make decision for each stock in the watchlist
                for list_stock in watchlist_stocks:
                    stock_symbol = list_stock['symbol']

                    try:
                        if stock_symbol in my_stocks:
                            print_with_timestamp(f"{stock_symbol} > Skipped: already processed")
                            continue
                        
                        simple_avg_decision, openai_decision, final_decision = make_decision(stock_symbol)
                        print_with_timestamp(f"{stock_symbol} > Decision: {final_decision} (Simple: {simple_avg_decision}, OpenAI: {openai_decision})")
                        
                        if final_decision == "buy":
                            buying_power = get_buying_power()
                            amount = round(buying_power * BUYING_AMOUNT_PERCENTAGE, 6)
                            amount = min(amount, MAX_BUYING_AMOUNT_USD)
                            amount = max(amount, MIN_BUYING_AMOUNT_USD)
                            amount = min(amount, buying_power)
                            buy_resp = buy_stock(stock_symbol, amount)
                            if 'id' in buy_resp:
                                bought_list.append(stock_symbol)
                                print_with_timestamp(f"{stock_symbol} > Bought {amount}$")
                            else:
                                print_with_timestamp(f"{stock_symbol} > Error buying {amount}$: {buy_resp}")
                        elif final_decision == "sell":
                            print_with_timestamp(f"{stock_symbol} > Skipped: not in my portfolio")
                        else:
                            print_with_timestamp(f"{stock_symbol} > Skipped: hold")
                    except Exception as e:
                        print_with_timestamp(f"{stock_symbol} > Error processing: {e}")
        
            print_with_timestamp(f"Bought: {bought_list}, Sold: {sold_list}")
            
            # Wait before the next trade
            time.sleep(BOT_RUN_INTERVAL_SECONDS)
        except Exception as e:
            print_with_timestamp(f"Error: {e}")

# Run the trading bot
if __name__ == '__main__':
    trading_bot()
