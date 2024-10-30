import robin_stocks.robinhood as rh
from openai import OpenAI
from datetime import datetime
import time
import pandas as pd
import numpy as np
import json
import re
import random
from config import *

# Initialize session and login
openai_client = OpenAI(api_key=OPENAI_API_KEY)
rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)


# Print log message with timestamp
def log(msg):
    print(f"[{datetime.now()}]  {msg}")


# Random pause between API calls
def random_pause(min_seconds=MIN_API_CALL_PAUSE_SECONDS, max_seconds=MAX_API_CALL_PAUSE_SECONDS):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


# Calculate moving averages for stock prices
def calculate_moving_averages(prices, short_window=50, long_window=200):
    short_mavg = pd.Series(prices).rolling(window=short_window).mean().iloc[-1]
    long_mavg = pd.Series(prices).rolling(window=long_window).mean().iloc[-1]
    return round(short_mavg, 2), round(long_mavg, 2)


# Enrich stock data with moving averages
def enrich_with_moving_averages(stock_data, symbol):
    prices = get_historical_data(symbol)
    if len(prices) >= 200:
        moving_avg_50, moving_avg_200 = calculate_moving_averages(prices)
        stock_data["50_day_mavg"] = moving_avg_50
        stock_data["200_day_mavg"] = moving_avg_200
    return stock_data


# Get analyst ratings for a stock by symbol
def enrich_with_analyst_ratings(stock_data, symbol):
    ratings = get_ratings(symbol)
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


# Get my buying power
def get_buying_power():
    random_pause()
    resp = rh.profiles.load_account_profile()
    if resp is None or 'buying_power' not in resp:
        raise Exception("Error getting profile data: No response")
    buying_power = float(resp['buying_power'])
    return buying_power


# Get my stocks
def get_my_stocks():
    random_pause()
    resp = rh.build_holdings()
    if resp is None:
        raise Exception("Error getting holdings data: No response")
    return resp


# Get watchlist stocks by name
def get_watchlist_stocks(name):
    random_pause()
    resp = rh.get_watchlist_by_name(name)
    if resp is None or 'results' not in resp:
        raise Exception(f"Error getting watchlist {name}: No response")
    return resp['results']


# Get analyst ratings for a stock by symbol
def get_ratings(symbol):
    random_pause()
    resp = rh.stocks.get_ratings(symbol)
    if resp is None:
        raise Exception(f"Error getting ratings for {symbol}: No response")
    return resp


# Get historical stock data by symbol
def get_historical_data(symbol, interval="day", span="year"):
    random_pause()
    resp = rh.stocks.get_stock_historicals(symbol, interval=interval, span=span)
    if resp is None:
        raise Exception(f"Error getting historical data for {symbol}: No response")
    prices = [float(day['close_price']) for day in resp]
    return prices


# Convert amount to quantity based on stock price
def amount_to_quantity(symbol, amount):
    random_pause()
    price_resp = rh.stocks.get_latest_price(symbol)
    if len(price_resp) == 0 or price_resp[0] is None:
        raise Exception(f"Error getting quote for {symbol}: No response")
    price = float(price_resp[0])
    quantity = round(amount / price, 6)
    return quantity


# Buy a stock by symbol and amount
def buy_stock(symbol, amount):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm buy for {symbol} at ${amount}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    quantity = amount_to_quantity(symbol, amount)
    random_pause()
    buy_resp = rh.orders.order_buy_fractional_by_quantity(symbol, quantity)
    if buy_resp is None:
        raise Exception(f"Error buying {symbol}: No response")
    return buy_resp


# Sell a stock by symbol and amount
def sell_stock(symbol, amount, available_quantity):
    if MODE == "demo":
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm sell for {symbol} at ${amount}? (yes/no): ")
        if confirm.lower() != "yes":
            return {"id": "cancelled"}

    quantity = amount_to_quantity(symbol, amount)
    if quantity > available_quantity:
        quantity = available_quantity
    random_pause()
    sell_resp = rh.orders.order_sell_fractional_by_quantity(symbol, quantity)
    if sell_resp is None:
        raise Exception(f"Error selling {symbol}: No response")
    return sell_resp


# Make AI-based decisions on stock portfolio and watchlist
def make_decisions(buying_power, portfolio_overview, watchlist_overview):
    ai_prompt = (
        f"Analyze the stock portfolio and watchlist to make investment decisions. "
        f"Suggest which stocks to sell first from the portfolio to increase buying power, "
        f"and then determine if any stock from either the portfolio or the watchlist is worth buying. "
        f"Return sell decisions in the order they should be executed to maximize buying power, "
        f"and then provide buy decisions based on the resulting buying power.\n\n"
        f"Portfolio overview:\n{json.dumps(portfolio_overview, indent=1)}\n\n"
        f"Watchlist overview:\n{json.dumps(watchlist_overview, indent=1)}\n\n"
        f"Total buying power: ${buying_power}.\n\n"
        f"Guidelines for buy/sell amounts:\n"
        f"- Min sell: ${MIN_SELLING_AMOUNT_USD}\n"
        f"- Max sell: ${MAX_SELLING_AMOUNT_USD}\n"
        f"- Min buy: ${MIN_BUYING_AMOUNT_USD}\n"
        f"- Max buy: ${MAX_BUYING_AMOUNT_USD}\n\n"
        f"Provide a JSON response in this format:\n"
        '[{"symbol": "<symbol>", "decision": "<decision>", "amount": <amount>}, ...]\n'
        "Decision options: buy, sell, hold\n"
        "Amount is the suggested amount to buy or sell in $\n"
        "Return only the JSON array, without explanation or extra text. "
        "If no decisions are made, return an empty array."
    )

    ai_response = openai_client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a precise trading robot that only responds in valid json after getting information about a stocks portfolio and watchlist."},
            {"role": "user", "content": ai_prompt}
        ]
    )

    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        decisions = json.loads(ai_content)
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())

    return decisions


# Make post-decisions adjustment based on trading results
def make_post_decisions_adjustment(buying_power, trading_results):
    ai_prompt = (
        "Analyze the trading results based on your previous decisions. "
        "Make adjustments if needed. "
        "Return sell decisions in the order they should be executed to maximize buying power, "
        "and then provide buy decisions based on the resulting buying power.\n\n"
        f"Trading results:\n{json.dumps(trading_results, indent=1)}\n\n"
        f"Total buying power: ${buying_power}.\n\n"
        "Guidelines for buy/sell amounts:\n"
        f"- Min sell: ${MIN_SELLING_AMOUNT_USD}\n"
        f"- Max sell: ${MAX_SELLING_AMOUNT_USD}\n"
        f"- Min buy: ${MIN_BUYING_AMOUNT_USD}\n"
        f"- Max buy: ${MAX_BUYING_AMOUNT_USD}\n\n"
        "Provide a JSON response in this format:\n"
        '[{"symbol": "<symbol>", "decision": "<decision>", "amount": <amount>}, ...]\n'
        "Decision options: buy, sell, hold\n"
        "Amount is the suggested amount to buy or sell in $\n"
        "Return only the JSON array, without explanation or extra text. "
        "If no decisions are made, return an empty array."
    )

    ai_response = openai_client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a precise trading robot that only responds in valid json after getting information about a trading results."},
            {"role": "user", "content": ai_prompt}
        ]
    )

    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        decisions = json.loads(ai_content)
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())

    return decisions


# Main trading bot function
def trading_bot():
    log("Getting my stocks to proceed...")
    my_stocks = get_my_stocks()

    log(f"Total stocks in portfolio: {len(my_stocks)}")

    log("Prepare portfolio overview for AI analysis...")
    portfolio_overview = {}
    for symbol, stock_data in my_stocks.items():
        portfolio_overview[symbol] = {
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
        portfolio_overview[symbol] = enrich_with_moving_averages(portfolio_overview[symbol], symbol)
        portfolio_overview[symbol] = enrich_with_analyst_ratings(portfolio_overview[symbol], symbol)

    log("Getting watchlist stocks to proceed...")
    watchlist_stocks = []
    for watchlist_name in WATCHLIST_NAMES:
        try:
            watchlist_stocks.extend(get_watchlist_stocks(watchlist_name))
            watchlist_stocks = [stock for stock in watchlist_stocks if stock['symbol'] not in my_stocks.keys()]
        except Exception as e:
            log(f"Error getting watchlist stocks for {watchlist_name}: {e}")

    log(f"Total watchlist stocks: {len(watchlist_stocks)}")

    if len(watchlist_stocks) > WATCHLIST_OVERVIEW_LIMIT:
        log(f"Limiting watchlist stocks to overview limit of {WATCHLIST_OVERVIEW_LIMIT} (random selection)...")
        watchlist_stocks = np.random.choice(watchlist_stocks, WATCHLIST_OVERVIEW_LIMIT, replace=False)

    log("Prepare watchlist overview for AI analysis...")
    watchlist_overview = {}
    for stock_data in watchlist_stocks:
        symbol = stock_data['symbol']
        watchlist_overview[symbol] = {
            "price": stock_data['price'],
        }
        watchlist_overview[symbol] = enrich_with_moving_averages(watchlist_overview[symbol], symbol)
        watchlist_overview[symbol] = enrich_with_analyst_ratings(watchlist_overview[symbol], symbol)

    if len(portfolio_overview) == 0 and len(watchlist_overview) == 0:
        log("No stocks to analyze, skipping AI-based decision-making...")
        return {}

    decisions_data = []
    trading_results = {}
    post_decisions_adjustment_count = 0

    try:
        log("Making AI-based decision...")
        buying_power = get_buying_power()
        decisions_data = make_decisions(buying_power, portfolio_overview, watchlist_overview)
    except Exception as e:
        log(f"Error making AI-based decision: {e}")

    log(f"Total decisions: {len(decisions_data)}")

    while len(decisions_data) > 0:
        log("Executing decisions...")
        for decision_data in decisions_data:
            symbol = decision_data['symbol']
            decision = decision_data['decision']
            amount = decision_data['amount']
            log(f"{symbol} > Decision: {decision} with amount ${amount}")

            if decision == "sell":
                try:
                    available_quantity = float(portfolio_overview[symbol]['quantity'])
                    sell_resp = sell_stock(symbol, amount, available_quantity)
                    if sell_resp and 'id' in sell_resp:
                        if sell_resp['id'] == "demo":
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "sell", "result": "success", "details": "Demo mode"}
                            log(f"{symbol} > Demo > Sold ${amount} worth of stock")
                        elif sell_resp['id'] == "cancelled":
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "sell", "result": "cancelled", "details": "Cancelled by user"}
                            log(f"{symbol} > Sell cancelled by user")
                        else:
                            details = {
                                "quantity": sell_resp['quantity'],
                                "price": sell_resp['price'],
                                "fees": sell_resp['fees'],
                            }
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "sell", "result": "success", "details": details}
                            log(f"{symbol} > Sold ${amount} worth of stock")
                    else:
                        details = sell_resp['detail'] if 'detail' in sell_resp else sell_resp
                        trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "sell", "result": "error", "details": details}
                        log(f"{symbol} > Error selling: {details}")
                except Exception as e:
                    trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "sell", "result": "error", "details": str(e)}
                    log(f"{symbol} > Error selling: {e}")

            if decision == "buy":
                try:
                    buy_resp = buy_stock(symbol, amount)
                    if buy_resp and 'id' in buy_resp:
                        if buy_resp['id'] == "demo":
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "buy", "result": "success", "details": "Demo mode"}
                            log(f"{symbol} > Demo > Bought ${amount} worth of stock")
                        elif buy_resp['id'] == "cancelled":
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "buy", "result": "cancelled", "details": "Cancelled by user"}
                            log(f"{symbol} > Buy cancelled by user")
                        else:
                            details = {
                                "quantity": buy_resp['quantity'],
                                "price": buy_resp['price'],
                                "fees": buy_resp['fees'],
                            }
                            trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "buy", "result": "success", "details": details}
                            log(f"{symbol} > Bought ${amount} worth of stock")
                    else:
                        details = buy_resp['detail'] if 'detail' in buy_resp else buy_resp
                        trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "buy", "result": "error", "details": details}
                        log(f"{symbol} > Error buying: {details}")
                except Exception as e:
                    trading_results[symbol] = {"symbol": symbol, "amount": amount, "decision": "buy", "result": "error", "details": str(e)}
                    log(f"{symbol} > Error buying: {e}")

        if post_decisions_adjustment_count >= MAX_POST_DECISIONS_ADJUSTMENTS:
            break

        try:
            log("Making AI-based post-decision analysis...")
            buying_power = get_buying_power()
            decisions_data = make_post_decisions_adjustment(buying_power, trading_results)
            post_decisions_adjustment_count += 1
        except Exception as e:
            log(f"Error making post-decision analysis: {e}")
            break

        log(f"Total post-decision adjustments: {len(decisions_data)}")

    return trading_results


# Run trading bot in a loop
def main():
    while True:
        try:
            market_hours = rh.get_market_hours(MARKET_MIC, datetime.now().strftime('%Y-%m-%d'))
            if market_hours and market_hours['is_open']:
                run_interval_seconds = RUN_INTERVAL_SECONDS
                log(f"Market {MARKET_MIC} is open, running trading bot in {MODE} mode...")
                trading_results = trading_bot()
                total_sold = sum([result['amount'] for result in trading_results.values() if result['decision'] == "sell" and result['result'] == "success"])
                total_bought = sum([result['amount'] for result in trading_results.values() if result['decision'] == "buy" and result['result'] == "success"])
                log(f"Total sold: ${total_sold}, Total bought: ${total_bought}")
            else:
                run_interval_seconds = 60
                log("Market is closed, waiting for next run...")
        except Exception as e:
            run_interval_seconds = 60
            log(f"Trading bot error: {e}")

        log(f"Waiting for {run_interval_seconds} seconds...")
        time.sleep(run_interval_seconds)


# Run the main function
if __name__ == '__main__':
    main()
