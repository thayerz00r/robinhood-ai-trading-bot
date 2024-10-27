import robin_stocks.robinhood as rh
from openai import OpenAI
from datetime import datetime
import time
import pandas as pd
import json
import re
from config import *

openai_client = OpenAI(api_key=OPENAI_API_KEY)


def print_with_timestamp(msg):
    print(f"[{datetime.now()}]  {msg}")


def login_to_robinhood():
    rh.login(ROBINHOOD_USERNAME, ROBINHOOD_PASSWORD)


def get_historical_data(stock_symbol, interval="day", span="year"):
    historical_data = rh.stocks.get_stock_historicals(stock_symbol, interval=interval, span=span)
    prices = [float(day['close_price']) for day in historical_data]
    return prices


def calculate_moving_averages(prices, short_window=50, long_window=200):
    short_mavg = pd.Series(prices).rolling(window=short_window).mean().iloc[-1]
    long_mavg = pd.Series(prices).rolling(window=long_window).mean().iloc[-1]
    return round(short_mavg, 2), round(long_mavg, 2)


def buy_stock(stock_symbol, amount):
    if MODE == "demo":
        print_with_timestamp(f"Demo buy action for {stock_symbol} at ${amount}")
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm buy for {stock_symbol} at {amount}$? (yes/no): ")
        if confirm.lower() != "yes":
            print_with_timestamp(f"Buy cancelled for {stock_symbol}")
            return {"id": "cancelled"}

    quote = rh.stocks.get_latest_price(stock_symbol)
    price = float(quote[0])
    quantity = round(amount / price, 6)
    return rh.orders.order_buy_fractional_by_quantity(stock_symbol, quantity)


def sell_stock(stock_symbol, quantity):
    if MODE == "demo":
        print_with_timestamp(f"Demo sell action for {stock_symbol} for {quantity} quantity")
        return {"id": "demo"}

    if MODE == "manual":
        confirm = input(f"Confirm sell for {stock_symbol} for {quantity} quantity? (yes/no): ")
        if confirm.lower() != "yes":
            print_with_timestamp(f"Sell cancelled for {stock_symbol}")
            return {"id": "cancelled"}

    return rh.orders.order_sell_fractional_by_quantity(stock_symbol, quantity)


# Make a decision to buy or sell based on AI prompt
def make_decision(stock_symbol, stock_quantity, buying_power):
    # Get historical data
    prices = get_historical_data(stock_symbol)
    if len(prices) < 200:
        raise Exception("Not enough data to calculate moving averages")

    # Calculate moving averages
    moving_avg_50, moving_avg_200 = calculate_moving_averages(prices, short_window=50, long_window=200)

    # AI prompt
    ai_prompt = (
        f"Stock symbol: {stock_symbol}\n"
        f"Current stock price: ${prices[-1]}\n"
        f"50-day moving average: ${moving_avg_50}\n"
        f"200-day moving average: ${moving_avg_200}\n\n"
        f"Your buying power is ${buying_power}.\n"
        f"You can buy up to ${MAX_BUYING_AMOUNT_USD} but not more than {BUYING_AMOUNT_PERCENTAGE * 100}% of your buying power.\n"
        f"Minimum buying amount is ${MIN_BUYING_AMOUNT_USD}.\n"
        f"Remember: you can't buy stocks if you don't have enough buying power.\n\n"
        f"Your stock quantity is {stock_quantity}.\n"
        f"You can sell up to ${MAX_SELLING_AMOUNT_USD} but not more than {SELLING_AMOUNT_PERCENTAGE * 100}% of your stock quantity.\n"
        f"Minimum selling amount is ${MIN_SELLING_AMOUNT_USD}.\n"
        f"Remember: you can't sell stocks if you don't have any.\n\n"
        f"Make a decision about {stock_symbol} based on the data above.\n"
        "Provide a structured JSON response in this format:\n"
        '{ "decision": "<decision>", "amount": <amount> }\n'
        "Decision options: buy, sell, hold\n"
        "Amount is the suggested amount to buy or sell in $\n"
        "Example: { 'decision': 'buy', 'amount': 10.0 }\n"
        "Return only the JSON, without explanation or extra text."
    )

    # Query OpenAI for insight
    ai_response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a precise financial trading advisor."},
            {"role": "user", "content": ai_prompt}
        ]
    )

    # Clean and parse AI decision
    try:
        ai_content = re.sub(r'```json|```', '', ai_response.choices[0].message.content.strip())
        ai_content = json.loads(ai_content)
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())

    ai_decision = ai_content['decision']
    ai_amount = float(ai_content['amount'])

    # Use OpenAI decision if valid
    if ai_decision not in ["buy", "sell", "hold"]:
        raise Exception("Invalid decision from OpenAI" + ai_decision)

    if ai_amount < 0:
        raise Exception("Invalid amount from OpenAI: " + str(ai_amount))

    return ai_decision, ai_amount


def get_buying_power():
    profile_data = rh.profiles.load_account_profile()
    buying_power = float(profile_data['buying_power'])
    return buying_power


def get_my_stocks():
    return rh.build_holdings()


def get_watch_list_stocks(name):
    resp = rh.get_watchlist_by_name(name)
    return resp['results']


def trading_bot():
    proceed_stock_symbols = set()
    bought_stock_symbols = set()
    sold_stock_symbols = set()

    print_with_timestamp("Getting my stocks to proceed...")
    my_stocks = get_my_stocks()
    for stock_symbol in my_stocks:
        proceed_stock_symbols.add(stock_symbol)

    print_with_timestamp("Getting watchlist stocks to proceed...")
    for watchlist_name in WATCHLIST_NAMES:
        try:
            watchlist_stocks = get_watch_list_stocks(watchlist_name)
            for watchlist_stock in watchlist_stocks:
                proceed_stock_symbols.add(watchlist_stock['symbol'])
        except Exception as e:
            print_with_timestamp(f"Error getting watchlist stocks for {watchlist_name}: {e}")

    print_with_timestamp(f"Stocks to proceed: {len(proceed_stock_symbols) if proceed_stock_symbols else 'None'}")

    if not proceed_stock_symbols:
        print_with_timestamp("No stocks to proceed. Exiting...")
        return

    for stock_symbol in proceed_stock_symbols:
        try:
            buying_power = get_buying_power()
            if buying_power < MIN_BUYING_AMOUNT_USD and stock_symbol not in my_stocks:
                print_with_timestamp(f"{stock_symbol} > Skipping decision-making: not enough buying power for non-owned stock")
                continue

            stock_quantity = float(my_stocks[stock_symbol]['quantity']) if stock_symbol in my_stocks else 0.0

            decision, amount = make_decision(stock_symbol, stock_quantity, buying_power)
            print_with_timestamp(f"{stock_symbol} > Decision: {decision}, Amount: ${amount}")

            if decision == "buy":
                if amount > MAX_BUYING_AMOUNT_USD:
                    amount = MAX_BUYING_AMOUNT_USD
                if amount < MIN_BUYING_AMOUNT_USD:
                    amount = MIN_BUYING_AMOUNT_USD
                if amount > buying_power:
                    amount = buying_power

                buy_resp = buy_stock(stock_symbol, amount)
                if 'id' in buy_resp:
                    bought_stock_symbols.add(stock_symbol)
                    print_with_timestamp(f"{stock_symbol} > Bought ${amount}")
                else:
                    print_with_timestamp(f"{stock_symbol} > Error buying ${amount}: {buy_resp}")

            elif decision == "sell":
                quote = rh.stocks.get_latest_price(stock_symbol)
                price = float(quote[0])
                quantity = round(amount / price, 6)
                if quantity > stock_quantity:
                    quantity = stock_quantity

                sell_resp = sell_stock(stock_symbol, quantity)
                if 'id' in sell_resp:
                    sold_stock_symbols.add(stock_symbol)
                    print_with_timestamp(f"{stock_symbol} > Sold {quantity} quantity")
                else:
                    print_with_timestamp(f"{stock_symbol} > Error selling {quantity} quantity: {sell_resp}")

        except Exception as e:
            print_with_timestamp(f"{stock_symbol} > Error processing: {e}")

    print_with_timestamp(f"Bought stocks: {bought_stock_symbols if bought_stock_symbols else 'None'}")
    print_with_timestamp(f"Sold stocks: {sold_stock_symbols if sold_stock_symbols else 'None'}")


# Run the trading bot in a loop
def main():
    print_with_timestamp("Logging in to Robinhood...")
    login_to_robinhood()

    while True:
        try:
            trading_bot()
            print_with_timestamp(f"Waiting for {RUN_INTERVAL_SECONDS} seconds...")
            time.sleep(RUN_INTERVAL_SECONDS)
        except Exception as e:
            print_with_timestamp(f"Trading bot error: {e}")
            time.sleep(30)


if __name__ == '__main__':
    main()
