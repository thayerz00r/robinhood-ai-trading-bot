import robin_stocks.robinhood as rh
from openai import OpenAI
from datetime import datetime
import time
import pandas as pd
import numpy as np
import json
import re
from config import *

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def print_with_timestamp(msg):
    print(f"[{datetime.now()}]  {msg}")


def login_to_robinhood():
    rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)


def get_buying_power():
    profile_data = rh.profiles.load_account_profile()
    buying_power = float(profile_data['buying_power'])
    return buying_power


def get_my_stocks():
    return rh.build_holdings()


def get_watchlist_stocks(name):
    resp = rh.get_watchlist_by_name(name)
    return resp['results']


def get_ratings(stock_symbol):
    return rh.stocks.get_ratings(stock_symbol)


def get_historical_data(stock_symbol, interval="day", span="year"):
    historical_data = rh.stocks.get_stock_historicals(stock_symbol, interval=interval, span=span)
    prices = [float(day['close_price']) for day in historical_data]
    return prices


def calculate_moving_averages(prices, short_window=50, long_window=200):
    short_mavg = pd.Series(prices).rolling(window=short_window).mean().iloc[-1]
    long_mavg = pd.Series(prices).rolling(window=long_window).mean().iloc[-1]
    return round(short_mavg, 2), round(long_mavg, 2)


def enrich_with_moving_averages(stock_data, stock_symbol):
    prices = get_historical_data(stock_symbol)
    if len(prices) >= 200:
        moving_avg_50, moving_avg_200 = calculate_moving_averages(prices)
        stock_data["50_day_mavg"] = moving_avg_50
        stock_data["200_day_mavg"] = moving_avg_200
    return stock_data


def enrich_with_analyst_ratings(stock_data, stock_symbol):
    ratings = get_ratings(stock_symbol)
    if 'ratings' in ratings and len(ratings['ratings']) > 0:
        last_sell_rating = next((rating for rating in ratings['ratings'] if rating['type'] == "sell"), None)
        last_buy_rating = next((rating for rating in ratings['ratings'] if rating['type'] == "buy"), None)
        if last_sell_rating:
            stock_data["analyst_rating_sell_text"] = last_sell_rating['text'].decode('utf-8')
        if last_buy_rating:
            stock_data["analyst_rating_buy_text"] = last_buy_rating['text'].decode('utf-8')
    if 'summary' in ratings and ratings['summary']:
        summary = ratings['summary']
        total_ratings = sum([summary['num_buy_ratings'], summary['num_hold_ratings'], summary['num_sell_ratings']])
        if total_ratings > 0:
            buy_percent = summary['num_buy_ratings'] / total_ratings * 100
            sell_percent = summary['num_sell_ratings'] / total_ratings * 100
            hold_percent = summary['num_hold_ratings'] / total_ratings * 100
            stock_data["analyst_rating_summary"] = f"Buy: {buy_percent:.0f}%, Sell: {sell_percent:.0f}%, Hold: {hold_percent:.0f}%"
    return stock_data


def buy_stock(stock_symbol, amount):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm buy for {stock_symbol} at ${amount}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    quote = rh.stocks.get_latest_price(stock_symbol)
    price = float(quote[0])
    quantity = round(amount / price, 6)
    return rh.orders.order_buy_fractional_by_quantity(stock_symbol, quantity)


def sell_stock(stock_symbol, amount):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm sell for {stock_symbol} at ${amount}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    quote = rh.stocks.get_latest_price(stock_symbol)
    price = float(quote[0])
    quantity = round(amount / price, 6)
    return rh.orders.order_sell_fractional_by_quantity(stock_symbol, quantity)


def make_decision(buying_power, portfolio_overview, watchlist_overview):
    # Updated AI prompt to include both portfolio and watchlist overviews and configuration parameters
    ai_prompt = (
        f"Analyze the following stock portfolio and watchlist to make investment decisions. "
        f"Suggest which stocks to sell first from the portfolio to increase buying power, "
        f"and then determine if any stock from either the portfolio or the watchlist is worth buying.\n\n"
        f"Portfolio overview:\n{json.dumps(portfolio_overview, indent=2)}\n\n"
        f"Watchlist overview:\n{json.dumps(watchlist_overview, indent=2)}\n\n"
        f"Total buying power: ${buying_power}.\n\n"
        f"Guidelines for buy/sell amounts:\n"
        f"- Minimum sell amount: ${MIN_SELLING_AMOUNT_USD}\n"
        f"- Maximum sell amount: ${MAX_SELLING_AMOUNT_USD}\n"
        f"- Minimum buy amount: ${MIN_BUYING_AMOUNT_USD}\n"
        f"- Maximum buy amount: ${MAX_BUYING_AMOUNT_USD}\n\n"
        f"Provide a structured JSON response in this format:\n"
        '[{"stock_symbol": "<symbol>", "decision": "<decision>", "amount": <amount>}, ...]\n'
        "Decision options: buy, sell, hold\n"
        "Amount is the suggested amount to buy or sell in $\n"
        "Return only the JSON array, without explanation or extra text."
    )

    # Query OpenAI for decision
    ai_response = openai_client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a precise financial trading advisor."},
            {"role": "user", "content": ai_prompt}
        ]
    )

    # Clean and parse AI decision
    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        decisions = json.loads(ai_content)
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())

    return decisions


def trading_bot():
    trading_results = {}

    print_with_timestamp(f"Running trading bot in {MODE} mode...")

    print_with_timestamp("Logging in to Robinhood...")
    login_to_robinhood()

    print_with_timestamp("Getting my stocks to proceed...")
    my_stocks = get_my_stocks()

    print_with_timestamp(f"Total stocks in portfolio: {len(my_stocks)}")
    print_with_timestamp("Prepare portfolio overview for AI analysis...")
    portfolio_overview = {}
    for stock_symbol, stock_data in my_stocks.items():
        portfolio_overview[stock_symbol] = {
            "price": stock_data['price'],
            "quantity": stock_data['quantity'],
            "average_buy_price": stock_data['average_buy_price'],
            "equity": stock_data['equity'],
            "percent_change": stock_data['percent_change'],
            "intraday_percent_change": stock_data['intraday_percent_change'],
            "equity_change": stock_data['equity_change'],
            "pe_ratio": stock_data['pe_ratio'],
            "percentage": stock_data['percentage'],
        }
        portfolio_overview[stock_symbol] = enrich_with_moving_averages(portfolio_overview[stock_symbol], stock_symbol)
        portfolio_overview[stock_symbol] = enrich_with_analyst_ratings(portfolio_overview[stock_symbol], stock_symbol)

    print_with_timestamp("Getting watchlist stocks to proceed...")
    watchlist_stocks = []
    for watchlist_name in WATCHLIST_NAMES:
        try:
            watchlist_stocks.extend(get_watchlist_stocks(watchlist_name))
            watchlist_stocks = [stock for stock in watchlist_stocks if stock['symbol'] not in my_stocks.keys()]
        except Exception as e:
            print_with_timestamp(f"Error getting watchlist stocks for {watchlist_name}: {e}")

    print_with_timestamp(f"Total watchlist stocks: {len(watchlist_stocks)}")
    if len(watchlist_stocks) > WATCHLIST_OVERVIEW_LIMIT:
        print_with_timestamp(f"Limiting watchlist stocks to overview limit of {WATCHLIST_OVERVIEW_LIMIT} (random selection)...")
        watchlist_stocks = np.random.choice(watchlist_stocks, WATCHLIST_OVERVIEW_LIMIT, replace=False)

    print_with_timestamp("Prepare watchlist overview for AI analysis...")
    watchlist_overview = {}
    for stock_data in watchlist_stocks:
        stock_symbol = stock_data['symbol']
        watchlist_overview[stock_symbol] = {
            "price": stock_data['price'],
        }
        watchlist_overview[stock_symbol] = enrich_with_moving_averages(watchlist_overview[stock_symbol], stock_symbol)
        watchlist_overview[stock_symbol] = enrich_with_analyst_ratings(watchlist_overview[stock_symbol], stock_symbol)

    try:
        print_with_timestamp("Making AI-based decision...")
        buying_power = get_buying_power()
        decisions = make_decision(buying_power, portfolio_overview, watchlist_overview)

        print_with_timestamp("Executing sell decisions...")
        for decision in decisions:
            if decision['decision'] == "sell":
                stock_symbol = decision['stock_symbol']
                amount = decision['amount']
                print_with_timestamp(f"{stock_symbol} > Decision: {decision['decision']} with amount ${amount}")
                sell_resp = sell_stock(stock_symbol, amount)
                if 'id' in sell_resp:
                    if sell_resp['id'] == "demo":
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "sell", "result": "success", "details": "Demo mode"}
                        print_with_timestamp(f"{stock_symbol} > Demo > Sold ${amount} worth of stock")
                    elif sell_resp['id'] == "cancelled":
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "sell", "result": "cancelled", "details": "Cancelled by user"}
                        print_with_timestamp(f"{stock_symbol} > Sell cancelled")
                    else:
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "sell", "result": "success", "details": sell_resp}
                        print_with_timestamp(f"{stock_symbol} > Sold ${amount} worth of stock")
                else:
                    trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "sell", "result": "error", "details": sell_resp}
                    print_with_timestamp(f"{stock_symbol} > Error selling: {sell_resp}")

        print_with_timestamp("Executing buy decisions...")
        for decision in decisions:
            if decision['decision'] == "buy":
                stock_symbol = decision['stock_symbol']
                amount = decision['amount']
                print_with_timestamp(f"{stock_symbol} > Decision: {decision['decision']} with amount ${amount}")
                buy_resp = buy_stock(stock_symbol, amount)
                if 'id' in buy_resp:
                    if buy_resp['id'] == "demo":
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "buy", "result": "success", "details": "Demo mode"}
                        print_with_timestamp(f"{stock_symbol} > Demo > Bought ${amount} worth of stock")
                    elif buy_resp['id'] == "cancelled":
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "buy", "result": "cancelled", "details": "Cancelled by user"}
                        print_with_timestamp(f"{stock_symbol} > Buy cancelled")
                    else:
                        trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "buy", "result": "success", "details": buy_resp}
                        print_with_timestamp(f"{stock_symbol} > Bought ${amount} worth of stock")
                else:
                    trading_results[stock_symbol] = {"stock_symbol": stock_symbol, "amount": amount, "decision": "buy", "result": "error", "details": buy_resp}
                    print_with_timestamp(f"{stock_symbol} > Error buying: {buy_resp}")

    except Exception as e:
        print_with_timestamp(f"Error in decision-making process: {e}")

    return trading_results


# Run the trading bot in a loop
def main():
    while True:
        try:
            # Do not run bot if it's not working hours (9am-4pm EST) and workdays (Mon-Fri)
            current_time = datetime.now()
            if not RUN_ON_WORKDAYS_ONLY or (current_time.weekday() < 5 and 9 <= current_time.hour < 16):
                trading_results = trading_bot()
                total_bought = sum([result['amount'] for result in trading_results.values() if result['decision'] == "buy" and result['result'] == "success"])
                total_sold = sum([result['amount'] for result in trading_results.values() if result['decision'] == "sell" and result['result'] == "success"])
                print_with_timestamp(f"Total bought: ${total_bought}, Total sold: ${total_sold}")
            else:
                print_with_timestamp("Outside of working hours, waiting for next run...")

            print_with_timestamp(f"Waiting for {RUN_INTERVAL_SECONDS} seconds...")
            time.sleep(RUN_INTERVAL_SECONDS)

        except Exception as e:
            print_with_timestamp(f"Trading bot error: {e}")
            time.sleep(30)


if __name__ == '__main__':
    main()
