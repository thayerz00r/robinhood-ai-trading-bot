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


def make_decision(portfolio_overview, buying_power):
    # AI prompt for comprehensive portfolio analysis
    ai_prompt = (
        f"Analyze the following stock portfolio and suggest which stocks to sell first to increase buying power, "
        f"and then if any stock is worth buying.\n\n"
        f"Portfolio overview:\n{json.dumps(portfolio_overview, indent=2)}\n\n"
        f"Total buying power: ${buying_power}.\n\n"
        f"Provide a structured JSON response in this format:\n"
        '[{"decision": "<decision>", "stock_symbol": "<symbol>", "amount": <amount>}, ...]\n'
        "Decision options: buy, sell, hold\n"
        "Amount is the suggested amount to buy or sell in $\n"
        "Return only the JSON array, without explanation or extra text."
    )

    # Query OpenAI for decision
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
        decisions = json.loads(ai_content)
    except json.JSONDecodeError as e:
        raise Exception("Invalid JSON response from OpenAI: " + ai_response.choices[0].message.content.strip())

    # Sort decisions: prioritize "sell" actions
    sell_decisions = [d for d in decisions if d["decision"] == "sell"]
    buy_decisions = [d for d in decisions if d["decision"] == "buy"]
    return sell_decisions + buy_decisions


def get_buying_power():
    profile_data = rh.profiles.load_account_profile()
    buying_power = float(profile_data['buying_power'])
    return buying_power


def get_my_stocks():
    raw_holdings = rh.build_holdings()
    portfolio = {}
    for symbol, details in raw_holdings.items():
        portfolio[symbol] = {k: v for k, v in details.items() if k not in ["id", "name"]}
    return portfolio


def trading_bot():
    print_with_timestamp(f"Running trading bot in {MODE} mode...")

    print_with_timestamp("Logging in to Robinhood...")
    login_to_robinhood()

    print_with_timestamp("Getting my stocks to proceed...")
    my_stocks = get_my_stocks()

    print_with_timestamp("Prepare portfolio overview for AI analysis...")
    portfolio_overview = {}
    for stock_symbol, stock_data in my_stocks.items():
        prices = get_historical_data(stock_symbol)
        if len(prices) >= 200:
            moving_avg_50, moving_avg_200 = calculate_moving_averages(prices)
            stock_data.update({
                "50_day_mavg": moving_avg_50,
                "200_day_mavg": moving_avg_200
            })
        portfolio_overview[stock_symbol] = stock_data

    try:
        print_with_timestamp("Making AI-based decision...")
        buying_power = get_buying_power()
        decisions = make_decision(portfolio_overview, buying_power)

        print_with_timestamp("Executing sell decisions...")
        for decision in decisions:
            stock_symbol = decision['stock_symbol']
            amount = decision['amount']
            print_with_timestamp(f"{stock_symbol} > Decision: {decision['decision']} with amount ${amount}")

            if decision['decision'] == "sell":
                sell_resp = sell_stock(stock_symbol, amount)
                if 'id' in sell_resp:
                    if sell_resp['id'] == "demo":
                        print_with_timestamp(f"{stock_symbol} > Demo > Sold ${amount} worth of stock")
                    elif sell_resp['id'] == "cancelled":
                        print_with_timestamp(f"{stock_symbol} > Sell cancelled")
                    else:
                        print_with_timestamp(f"{stock_symbol} > Sold ${amount} worth of stock")
                else:
                    print_with_timestamp(f"{stock_symbol} > Error selling: {sell_resp}")

        print_with_timestamp("Executing buy decisions...")
        for decision in decisions:
            if decision['decision'] == "buy":
                buying_power = get_buying_power()

                stock_symbol = decision['stock_symbol']
                amount = decision['amount']
                print_with_timestamp(f"{stock_symbol} > Decision: {decision['decision']} with amount ${amount}")

                if amount <= buying_power:
                    buy_resp = buy_stock(stock_symbol, amount)
                    if 'id' in buy_resp:
                        if buy_resp['id'] == "demo":
                            print_with_timestamp(f"{stock_symbol} > Demo > Bought ${amount} worth of stock")
                        elif buy_resp['id'] == "cancelled":
                            print_with_timestamp(f"{stock_symbol} > Buy cancelled")
                        else:
                            print_with_timestamp(f"{stock_symbol} > Bought ${amount} worth of stock")
                    else:
                        print_with_timestamp(f"{stock_symbol} > Error buying: {buy_resp}")
                else:
                    print_with_timestamp(f"{stock_symbol} > Not enough buying power to buy ${amount}")

    except Exception as e:
        print_with_timestamp(f"Error in decision-making process: {e}")


# Run the trading bot in a loop
def main():
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
