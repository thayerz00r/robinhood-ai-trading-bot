import robin_stocks.robinhood as rh
from openai import OpenAI
import time
import pandas as pd
import json
import re
from pytz import timezone
from config import *
from log import *


# Initialize session and login
openai_client = OpenAI(api_key=OPENAI_API_KEY)
rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)


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
            stock_data["robinhood_analyst_sell_opinion"] = last_sell_rating['text'].decode('utf-8')
        if last_buy_rating:
            stock_data["robinhood_analyst_buy_opinion"] = last_buy_rating['text'].decode('utf-8')
    if 'summary' in ratings and ratings['summary']:
        summary = ratings['summary']
        total_ratings = sum([summary['num_buy_ratings'], summary['num_hold_ratings'], summary['num_sell_ratings']])
        if total_ratings > 0:
            buy_percent = summary['num_buy_ratings'] / total_ratings * 100
            sell_percent = summary['num_sell_ratings'] / total_ratings * 100
            hold_percent = summary['num_hold_ratings'] / total_ratings * 100
            stock_data["robinhood_analyst_summary_distribution"] = f"sell: {sell_percent:.0f}%, buy: {buy_percent:.0f}%, hold: {hold_percent:.0f}%"
    return stock_data


# Get my buying power
def get_buying_power():
    resp = rh_run_with_retries(rh.profiles.load_account_profile)
    if resp is None or 'buying_power' not in resp:
        raise Exception("Error getting profile data: No response")
    buying_power = round_money(resp['buying_power'])
    return buying_power


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
    prices = [round_money(day['close_price']) for day in resp]
    return prices


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


# Make AI request to OpenAI API
def make_ai_request(prompt):
    ai_resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    return ai_resp


# Parse AI response
def parse_ai_response(ai_response):
    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        decisions = json.loads(ai_content)
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())
    return decisions


# Get amount guidelines
def get_amount_guidelines():
    sell_guidelines = []
    if MIN_SELLING_AMOUNT_USD is not False:
        sell_guidelines.append(f"Minimum {MIN_SELLING_AMOUNT_USD} USD")
    if MAX_SELLING_AMOUNT_USD is not False:
        sell_guidelines.append(f"Maximum {MAX_SELLING_AMOUNT_USD} USD")
    sell_guidelines = ", ".join(sell_guidelines) if sell_guidelines else None

    buy_guidelines = []
    if MIN_BUYING_AMOUNT_USD is not False:
        buy_guidelines.append(f"Minimum {MIN_BUYING_AMOUNT_USD} USD")
    if MAX_BUYING_AMOUNT_USD is not False:
        buy_guidelines.append(f"Maximum {MAX_BUYING_AMOUNT_USD} USD")
    buy_guidelines = ", ".join(buy_guidelines) if buy_guidelines else None

    return sell_guidelines, buy_guidelines


# Make AI-based decisions on stock portfolio and watchlist
def make_ai_decisions(buying_power, portfolio_overview, watchlist_overview):
    sell_guidelines, buy_guidelines = get_amount_guidelines()
    ai_prompt = (
        "**Decision-Making AI Prompt:**\n\n"
        "**Context:**\n"
        f"You are an investment advisor managing a stock portfolio and watchlist. Every {RUN_INTERVAL_SECONDS} seconds, you analyze market conditions to make informed investment decisions.{chr(10)}{chr(10)}"
        "**Task:**\n"
        "Analyze the provided portfolio and watchlist data to recommend:\n"
        "1. Stocks to sell, prioritizing those that maximize buying power and profit potential.\n"
        "2. Stocks to buy that align with available funds and current market conditions.\n\n"
        "**Constraints:**\n"
        f"- Maintain a portfolio size of fewer than {PORTFOLIO_LIMIT} stocks.{chr(10)}"
        f"- Total Buying Power: {buying_power} USD initially.{chr(10)}"
        f"{f'- Sell Amounts Guidelines: {sell_guidelines}{chr(10)}' if sell_guidelines else ''}"
        f"{f'- Buy Amounts Guidelines: {buy_guidelines}{chr(10)}' if buy_guidelines else ''}{chr(10)}"
        "**Portfolio Overview:**\n"
        "```json\n"
        f"{json.dumps(portfolio_overview, indent=1)}{chr(10)}"
        "```\n\n"
        "**Watchlist Overview:**\n"
        "```json\n"
        f"{json.dumps(watchlist_overview, indent=1)}{chr(10)}"
        "```\n\n"
        "**Response Format:**\n"
        "Return your decisions in a JSON array with this structure:\n"
        "```json\n"
        "[\n"
        '  {"symbol": "<symbol>", "decision": "<decision>", "quantity": <quantity>},\n'
        "  ...\n"
        "]\n"
        "```\n"
        "- `symbol`: Stock ticker symbol.\n"
        "- `decision`: One of `buy`, `sell`, or `hold`.\n"
        "- `quantity`: Recommended transaction quantity.\n\n"
        "**Instructions:**\n"
        "- Provide only the JSON output with no additional text.\n"
        "- Return an empty array if no actions are necessary."
    )
    log_debug(f"AI making-decisions prompt:{chr(10)}{ai_prompt}")
    ai_response = make_ai_request(ai_prompt)
    log_debug(f"AI making-decisions response:{chr(10)}{ai_response.choices[0].message.content.strip()}")
    decisions = parse_ai_response(ai_response)
    return decisions


# Make post-decisions adjustment based on trading results
def make_ai_post_decisions_adjustment(buying_power, trading_results):
    sell_guidelines, buy_guidelines = get_amount_guidelines()
    ai_prompt = (
        "**Post-Decision Adjustments AI Prompt:**\n\n"
        "**Context:**\n"
        "You are an investment advisor tasked with reviewing and adjusting prior trading decisions. Your goal is to optimize buying power and profit potential by analyzing trading results and making necessary changes.\n\n"
        "**Task:**\n"
        "1. Review previous trading outcomes and resolve any errors.\n"
        "2. Reorder and adjust sell decisions to enhance buying power.\n"
        "3. Update buy recommendations based on the newly available buying power.\n\n"
        "**Constraints:**\n"
        f"- Maintain a portfolio size of fewer than {PORTFOLIO_LIMIT} stocks.{chr(10)}"
        f"- Total Buying Power: {buying_power} USD initially.{chr(10)}"
        f"{f'- Sell Amounts Guidelines: {sell_guidelines}{chr(10)}' if sell_guidelines else ''}"
        f"{f'- Buy Amounts Guidelines: {buy_guidelines}{chr(10)}' if buy_guidelines else ''}{chr(10)}"
        "**Trading Results:**\n"
        "```json\n"
        f"{json.dumps(trading_results, indent=1)}{chr(10)}"
        "```\n\n"
        "**Response Format:**\n"
        "Return your decisions in a JSON array with this structure:\n"
        "```json\n"
        "[\n"
        '  {"symbol": "<symbol>", "decision": "<decision>", "quantity": <quantity>},\n'
        "  ...\n"
        "]\n"
        "```\n"
        "- `symbol`: Stock ticker symbol.\n"
        "- `decision`: One of `buy`, `sell`, or `hold`.\n"
        "- `quantity`: Recommended transaction quantity.\n\n"
        "**Instructions:**\n"
        "- Provide only the JSON output with no additional text.\n"
        "- Return an empty array if no actions are necessary."
    )
    log_debug(f"AI post-decisions-adjustment prompt:{chr(10)}{ai_prompt}")
    ai_response = make_ai_request(ai_prompt)
    log_debug(f"AI post-decisions-adjustment response:{chr(10)}{ai_response.choices[0].message.content.strip()}")
    decisions = parse_ai_response(ai_response)
    return decisions


# Limit watchlist stocks based on the current day of the month
from datetime import datetime, timedelta

# Limit watchlist stocks based on the current week number
def limit_watchlist_stocks(watchlist_stocks, limit):
    if len(watchlist_stocks) <= limit:
        return watchlist_stocks

    # Sort watchlist stocks by symbol
    watchlist_stocks = sorted(watchlist_stocks, key=lambda x: x['symbol'])

    # Get the current month number
    current_month = datetime.now().month

    # Calculate the number of parts
    num_parts = (len(watchlist_stocks) + limit - 1) // limit  # Ceiling division

    # Determine the part to return based on the current month number
    part_index = (current_month - 1) % num_parts
    start_index = part_index * limit
    end_index = min(start_index + limit, len(watchlist_stocks))

    return watchlist_stocks[start_index:end_index]


# Main trading bot function
def trading_bot():
    log_info("Getting portfolio stocks...")
    portfolio_stocks = get_portfolio_stocks()

    log_debug(f"Portfolio stocks total: {len(portfolio_stocks)}")

    portfolio_stocks_value = 0
    for stock in portfolio_stocks.values():
        portfolio_stocks_value += float(stock['price']) * float(stock['quantity'])
    portfolio = [f"{symbol} ({round(float(stock['price']) * float(stock['quantity']) / portfolio_stocks_value * 100, 2)}%)" for symbol, stock in portfolio_stocks.items()]
    log_info(f"Portfolio stocks to proceed: {"None" if len(portfolio) == 0 else ', '.join(portfolio)}")

    log_info("Prepare portfolio stocks for AI analysis...")
    portfolio_overview = {}
    for symbol, stock_data in portfolio_stocks.items():
        portfolio_overview[symbol] = extract_my_stocks_data(stock_data)
        portfolio_overview[symbol] = enrich_with_moving_averages(portfolio_overview[symbol], symbol)
        portfolio_overview[symbol] = enrich_with_analyst_ratings(portfolio_overview[symbol], symbol)

    log_info("Getting watchlist stocks...")
    watchlist_stocks = []
    for watchlist_name in WATCHLIST_NAMES:
        try:
            watchlist_stocks.extend(get_watchlist_stocks(watchlist_name))
            watchlist_stocks = [dict(t) for t in {tuple(d.items()) for d in watchlist_stocks}]
        except Exception as e:
            log_error(f"Error getting watchlist stocks for {watchlist_name}: {e}")

    log_debug(f"Watchlist stocks total: {len(watchlist_stocks)}")

    watchlist_overview = {}
    if len(watchlist_stocks) > 0:
        log_debug(f"Limiting watchlist stocks to overview limit of {WATCHLIST_OVERVIEW_LIMIT}...")
        watchlist_stocks = limit_watchlist_stocks(watchlist_stocks, WATCHLIST_OVERVIEW_LIMIT)

        log_debug(f"Removing portfolio stocks from watchlist...")
        watchlist_stocks = [stock for stock in watchlist_stocks if stock['symbol'] not in portfolio_stocks.keys()]

        log_info(f"Watchlist stocks to proceed: {', '.join([stock['symbol'] for stock in watchlist_stocks])}")

        log_info("Prepare watchlist overview for AI analysis...")
        for stock_data in watchlist_stocks:
            symbol = stock_data['symbol']
            watchlist_overview[symbol] = extract_watchlist_data(stock_data)
            watchlist_overview[symbol] = enrich_with_moving_averages(watchlist_overview[symbol], symbol)
            watchlist_overview[symbol] = enrich_with_analyst_ratings(watchlist_overview[symbol], symbol)

    if len(portfolio_overview) == 0 and len(watchlist_overview) == 0:
        log_warning("No stocks to analyze, skipping AI-based decision-making...")
        return {}

    decisions_data = []
    trading_results = {}
    post_decisions_adjustment_count = 0

    try:
        log_info("Making AI-based decision...")
        buying_power = round_money(get_buying_power())
        decisions_data = make_ai_decisions(buying_power, portfolio_overview, watchlist_overview)
    except Exception as e:
        log_error(f"Error making AI-based decision: {e}")


    while len(decisions_data) > 0:
        log_debug(f"Total decisions: {len(decisions_data)}")
        log_debug(f"Decisions:{chr(10)}{json.dumps(decisions_data, indent=1)}")

        log_info("Executing decisions...")
        for decision_data in decisions_data:
            symbol = decision_data['symbol']
            decision = decision_data['decision']
            quantity = decision_data['quantity']
            log_info(f"{symbol} > Decision: {decision} of {quantity}")

            if decision == "sell":
                try:
                    sell_resp = sell_stock(symbol, quantity)
                    if sell_resp and 'id' in sell_resp:
                        if sell_resp['id'] == "demo":
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "success", "details": "Demo mode"}
                            log_info(f"{symbol} > Demo > Sold {quantity} stocks")
                        elif sell_resp['id'] == "cancelled":
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "cancelled", "details": "Cancelled by user"}
                            log_info(f"{symbol} > Sell cancelled by user")
                        else:
                            details = extract_sell_response_data(sell_resp)
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "success", "details": details}
                            log_info(f"{symbol} > Sold {quantity} stocks")
                    else:
                        details = sell_resp['detail'] if 'detail' in sell_resp else sell_resp
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "error", "details": details}
                        log_error(f"{symbol} > Error selling: {details}")
                except Exception as e:
                    trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "sell", "result": "error", "details": str(e)}
                    log_error(f"{symbol} > Error selling: {e}")

            if decision == "buy":
                try:
                    buy_resp = buy_stock(symbol, quantity)
                    if buy_resp and 'id' in buy_resp:
                        if buy_resp['id'] == "demo":
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "success", "details": "Demo mode"}
                            log_info(f"{symbol} > Demo > Bought {quantity} stocks")
                        elif buy_resp['id'] == "cancelled":
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "cancelled", "details": "Cancelled by user"}
                            log_info(f"{symbol} > Buy cancelled by user")
                        else:
                            details = extract_buy_response_data(buy_resp)
                            trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "success", "details": details}
                            log_info(f"{symbol} > Bought {quantity} stocks")
                    else:
                        details = buy_resp['detail'] if 'detail' in buy_resp else buy_resp
                        trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "error", "details": details}
                        log_error(f"{symbol} > Error buying: {details}")
                except Exception as e:
                    trading_results[symbol] = {"symbol": symbol, "quantity": quantity, "decision": "buy", "result": "error", "details": str(e)}
                    log_error(f"{symbol} > Error buying: {e}")

        if (MAX_POST_DECISIONS_ADJUSTMENTS is False
                or post_decisions_adjustment_count >= MAX_POST_DECISIONS_ADJUSTMENTS):
            break

        try:
            post_decisions_adjustment_count += 1
            log_info(f"Making AI-based post-decision analysis, attempt: {post_decisions_adjustment_count}/{MAX_POST_DECISIONS_ADJUSTMENTS}...")
            buying_power = round_money(get_buying_power())
            decisions_data = make_ai_post_decisions_adjustment(buying_power, trading_results)
            log_debug(f"Total post-decision adjustments: {len(decisions_data)}")
        except Exception as e:
            log_error(f"Error making post-decision analysis: {e}")
            break

    return trading_results


# Run trading bot in a loop
def main():
    while True:
        try:
            if is_market_open():
                run_interval_seconds = RUN_INTERVAL_SECONDS
                log_info(f"Market is open, running trading bot in {MODE} mode...")

                trading_results = trading_bot()

                sold_stocks = [f"{result['symbol']} ({result['quantity']})" for result in trading_results.values() if result['decision'] == "sell" and result['result'] == "success"]
                bought_stocks = [f"{result['symbol']} ({result['quantity']})" for result in trading_results.values() if result['decision'] == "buy" and result['result'] == "success"]
                errors = [f"{result['symbol']} ({result['details']})" for result in trading_results.values() if result['result'] == "error"]
                log_info(f"Sold: {"None" if len(sold_stocks) == 0 else ', '.join(sold_stocks)}")
                log_info(f"Bought: {"None" if len(bought_stocks) == 0 else ', '.join(bought_stocks)}")
                log_info(f"Errors: {"None" if len(errors) == 0 else ', '.join(errors)}")
            else:
                run_interval_seconds = 60
                log_info("Market is closed, waiting for next run...")
        except Exception as e:
            run_interval_seconds = 60
            log_error(f"Trading bot error: {e}")

        log_info(f"Waiting for {run_interval_seconds} seconds...")
        time.sleep(run_interval_seconds)


# Run the main function
if __name__ == '__main__':
    confirm = input(f"Are you sure you want to run the bot in {MODE} mode? (yes/no): ")
    if confirm.lower() != "yes":
        log_warning("Exiting the bot...")
        exit()
    main()
