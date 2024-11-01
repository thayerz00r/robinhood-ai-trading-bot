# 🤖 Robinhood AI Trading Bot
## ⚡ TL;DR
Once you've added your OpenAI API Key and Robinhood credentials, and run this bot in "Auto" mode, it will analyze your portfolio stocks and some of your watchlist stocks (if available). 
It calculates moving averages for these stocks, checks Robinhood analyst ratings (covering what "bulls" and "bears" say), feeds this data to OpenAI, and asks the AI to decide on actions for each stock (sell, buy, or hold, including amount). 
It then directly executes all AI-made decisions.

So be smart — don’t run this bot in "Auto" mode right after your first test. 
This involves real money, and there’s no cancel button! 
Begin with "Demo" mode, which performs everything as in "Auto" mode except the actual sell and buy actions, which are just printed as if executed.

Then, try "Manual" mode, where the bot asks for confirmation before each sell or buy action.

P.S. I still run it in "Auto" mode, and, to be honest, I’m happy with the results so far.


## 🌟 Fun Part
Welcome to the Robinhood Trading Bot! This Python script pairs OpenAI's intelligence with Robinhood's trading power to help you automate and optimize your stock moves.


### Motivation
This is a scientific experiment to see how AI can trade stocks better than humans (or at least me). 


### Features
- **AI-Powered Trading**: Leverages OpenAI to provide smart, data-driven trading decisions.
- **Post-Decision Adjustments**: Refines trading moves based on trade outcomes.
- **Portfolio & Watchlist Integration**: Analyze and trade stocks from both your Robinhood portfolio and watchlist.
- **Customizable Parameters**: Set trading limits and conditions to fit your strategy.
- **Demo Mode**: Safely test trades without real execution.
- **Manual Mode**: Approve each trade individually.
- **Auto Mode**: Automate trades based on AI guidance.
- **Workday Schedule**: Align bot activity with market hours.
- **Logging**: Track bot activity and trade history in the console.


### How It Works
1. **Login to OpenAI**: Authenticates using your OpenAI API key.
2. **Login to Robinhood**: Logs into your Robinhood account with your credentials.
3. **Fetch Portfolio Stocks**: Retrieves stocks from your portfolio.
4. **Fetch Watchlist Stocks**: Retrieves a limited number of stocks from your watchlist, selecting randomly if needed to meet the limit.
5. **Analyze Stock Prices and Ratings**: Calculates moving averages and includes Robinhood analyst ratings.
6. **AI-Powered Decisions**: Sends stock data to OpenAI, receiving trading decisions (sell, buy, or hold) for each stock.
7. **Execute Trades**: Executes initial trading decisions.
8. **Post-Decision Adjustments**: Adjusts trades based on executed outcomes.
9. **Execute Adjusted Trades**: Executes refined trading decisions.
10. **Repeat**: Continues to analyze, trade, and adjust as market conditions evolve.


#### Analyze Stock Prices and Ratings System
The bot's analytical system incorporates moving averages and Robinhood analyst ratings to inform trading decisions:
1. **Moving Averages**: The bot calculates moving averages (50-day and 200-day) for each stock to evaluate price trends and identify optimal buy and sell points.
2. **Robinhood Analyst Ratings**: The bot fetches bullish and bearish ratings from Robinhood for each stock, providing additional insights into market sentiment and potential price movements.

This is Robinhood's analyst rating system example:

![Robinhood Analyst Ratings](images/robinhood_analyst_ratings.png)


#### AI-Powered Decision-Making System
The bot leverages OpenAI to make data-driven trading decisions based on the stock data:
1. **Input Data**: The bot feeds the stock data (moving averages, analyst ratings) to OpenAI.
2. **Output Data**: OpenAI provides trading decisions (sell, buy, or hold) for each stock.

Decision-making AI-prompt example:  
```
You are an investment advisor managing a stock portfolio and watchlist. Analyze both and suggest which stocks to sell first to maximize buying power and profit potential, followed by any potential buy opportunities that align with available funds and market conditions. Only respond in JSON format.

Portfolio:
{
 "NVDA": {
  "price": 136.13,
  "quantity": 0.004276,
  "average_buy_price": 141.65,
  "50_day_mavg_price": 125.22,
  "200_day_mavg_price": 104.33,
  "robinhood_analyst_sell_opinion": "Nvidia\u2019s gaming GPU business has often seen boom-or-bust cycles based on PC demand and, more recently, cryptocurrency mining.",
  "robinhood_analyst_buy_opinion": "The firm has a first-mover advantage in the autonomous driving market that could lead to widespread adoption of its Drive PX self-driving platform.",
  "robinhood_analyst_summary_distribution": "sell: 0%, buy: 92%, hold: 8%"
 },
 "MSFT": {
  "price": 414.13,
  "quantity": 0.000399,
  "average_buy_price": 410.07,
  "50_day_mavg_price": 420.79,
  "200_day_mavg_price": 420.75,
  "robinhood_analyst_sell_opinion": "Microsoft is not the top player in its key sources of growth, notably Azure and Dynamics.",
  "robinhood_analyst_buy_opinion": "Microsoft has monopoly like positions in various areas (OS, Office) that serve as cash cows to help drive Azure growth.",
  "robinhood_analyst_summary_distribution": "sell: 2%, buy: 91%, hold: 7%"
 },
 ...
}

Watchlist:
{
 "VRT": {
  "price": 108.72,
  "50_day_mavg_price": 96.23,
  "200_day_mavg_price": 84.28,
  "robinhood_analyst_summary_distribution": "sell: 0%, buy: 100%, hold: 0%"
 },
 "BB": {
  "price": 2.3,
  "50_day_mavg_price": 2.42,
  "200_day_mavg_price": 2.63,
  "robinhood_analyst_sell_opinion": "BlackBerry has yet to prove its ability to grow organically as a software company.",
  "robinhood_analyst_buy_opinion": "BlackBerry IVY\u2014the result of a partnership with Amazon Web Services\u2014could create a revolutionary software ecosystem for connected vehicles, allowing OEMs to process, analyze, and monetize massive amounts of vehicle data. ",
  "robinhood_analyst_summary_distribution": "sell: 0%, buy: 44%, hold: 56%"
 },
 ...
}

Total buying power (USD): 2.09

Sell amounts guidelines (USD): Min: 1.0, Max: 300.0
Buy amounts guidelines (USD): Min: 1.0, Max: 300.0

Response format:
[{"symbol": "<symbol>", "decision": "<decision>", "amount": <amount>}, ...]
Decision options: buy, sell, hold
Amount represents the recommended buy or sell amount in USD. Return only the JSON array; no explanations. If no decisions are necessary, return an empty array.
```

AI-response example:
```
[
    {"symbol": "AAPL", "decision": "sell", "amount": 1.0},
    {"symbol": "BL", "decision": "hold", "amount": 0.0},
    {"symbol": "EQIX", "decision": "buy", "amount": 1.0},
    ...
]
```


#### AI-Powered Post-Decision Adjustments System
The bot adjusts its trading decisions based on the outcomes of executed trades:
1. **Input Data**: The bot feeds the executed trades data to OpenAI.
2. **Output Data**: OpenAI provides adjustments to the trading decisions based on the trading results.

Post-decision adjustments AI-prompt example:  
```
You are an investment advisor responsible for reviewing and adjusting prior trading decisions. Analyze the provided trading results to ensure they maximize buying power and profit potential. Reorder sell decisions as needed to optimize buying power, then provide buy recommendations based on the updated buying power. Only respond in JSON format.

Trading results:
{
 "NVDA": {
  "symbol": "NVDA",
  "amount": 1.0,
  "decision": "sell",
  "result": "error",
  "details": "Not enough shares to sell."
 },
 "VRT": {
  "symbol": "VRT",
  "amount": 2.09,
  "decision": "buy",
  "result": "success",
  "details": {
   "quantity": 0.0192,
   "price": 108.76
  }
 },
 ...
}

Total buying power (USD): 0.0

Sell amounts guidelines (USD): Min: 1.0, Max: 300.0
Buy amounts guidelines (USD): Min: 1.0, Max: 300.0

Response format:
[{"symbol": "<symbol>", "decision": "<decision>", "amount": <amount>}, ...]
Decision options: buy, sell, hold
Amount represents the recommended buy or sell amount in USD. Return only the JSON array; no explanations. If no adjustments are necessary, return an empty array.
```

AI-response example:
```
[
    {"symbol": "AAPL", "decision": "sell", "amount": 1.5},
    ...
]
```


#### Logging System
The bot logs its activity and trading decisions in a console log.
Log example:
```
Are you sure you want to run the bot in auto mode? (yes/no): yes
[2024-11-01 11:06:58] [INFO]    Market is open, running trading bot in auto mode...
[2024-11-01 11:06:58] [INFO]    Getting portfolio stocks...
[2024-11-01 11:07:02] [INFO]    Portfolio stocks to proceed: NVDA (1.07%), MSFT (0.12%), SNAP (0.25%), NWSA (13.71%), ...
[2024-11-01 11:07:02] [INFO]    Prepare portfolio stocks for AI analysis...
[2024-11-01 11:07:07] [INFO]    Getting watchlist stocks...
[2024-11-01 11:07:08] [INFO]    Watchlist stocks to proceed: VRT, BB, VRNT, PBI, BMBL, IESC, WB, LITE, ...
[2024-11-01 11:07:08] [INFO]    Prepare watchlist overview for AI analysis...
[2024-11-01 11:07:09] [INFO]    Making AI-based decision...
[2024-11-01 11:07:21] [INFO]    Executing decisions...
[2024-11-01 11:07:21] [INFO]    NVDA > Decision: sell with amount $2.0
[2024-11-01 11:07:21] [ERROR]   NVDA > Sold $2.0 worth of stock
[2024-11-01 11:07:21] [INFO]    MSFT > Decision: sell with amount $1.0
[2024-11-01 11:07:21] [ERROR]   MSFT > Error selling: Not enough shares to sell.
[2024-11-01 11:07:22] [INFO]    VRT > Decision: buy with amount $2.09
[2024-11-01 11:07:23] [INFO]    VRT > Bought $2.09 worth of stock
[2024-11-01 11:07:23] [INFO]    SNAP > Decision: hold with amount $0.0
[2024-11-01 11:07:23] [INFO]    VIAV > Decision: hold with amount $0.0
[2024-11-01 11:07:23] [INFO]    Making AI-based post-decision analysis, attempt: 1/2...
[2024-11-01 11:07:24] [INFO]    Stocks sold: NVDA ($2.0)
[2024-11-01 11:07:24] [INFO]    Stocks bought: VRT ($2.09)
[2024-11-01 11:07:24] [INFO]    Errors: MSFT (Not enough shares to sell.)
[2024-11-01 11:07:24] [INFO]    Waiting for 600 seconds...
```


## 🥱 Boring Part
### Install
1. Clone the repository:
    ```sh
    git clone https://github.com/siropkin/robinhood-ai-trading-bot.git
    cd robinhood-ai-trading-bot
    ```

2. Install dependencies:
    ```sh
    pip install robin_stocks openai pandas numpy
    ```


### Config
Clone `config.py.example` to `config.py` and fill in the required parameters:
   ```sh
   cp config.py.example config.py
   ```

Configuration parameters:
```python
# Credentials
OPENAI_API_KEY = "..."                      # OpenAI API key
ROBINHOOD_USERNAME = "..."                  # Robinhood username
ROBINHOOD_PASSWORD = "..."                  # Robinhood password

# Basic config parameters
MODE = "demo"                               # Trading mode (demo, auto, manual)
LOG_LEVEL = "INFO"                          # Log level (DEBUG, INFO)
RUN_INTERVAL_SECONDS = 600                  # Trading interval in seconds (if the market is open)

# Robinhood config parameters
WATCHLIST_NAMES = []                        # Watchlist names (can be empty, or "My First List", "My Second List", etc.)
WATCHLIST_OVERVIEW_LIMIT = 10               # Number of stocks to process in decision-making (e.g. 20)

# OpenAI config params
MAX_POST_DECISIONS_ADJUSTMENTS = 1          # Maximum number of adjustments to make (0 - disable adjustments)
OPENAI_MODEL_NAME = "gpt-4o-mini"           # OpenAI model name

# Trading parameters
MIN_SELLING_AMOUNT_USD = 1.0                # Minimum sell amount in USD
MAX_SELLING_AMOUNT_USD = 10.0               # Maximum sell amount in USD
MIN_BUYING_AMOUNT_USD = 1.0                 # Minimum buy amount in USD
MAX_BUYING_AMOUNT_USD = 10.0                # Maximum buy amount in USD
```

### Run
To start the bot, run the following command in your terminal:
   ```sh
   python main.py
   ```


## ⚠️ Disclaimer
This bot is for educational purposes only. Trading stocks involves risk, and you should only trade with money you can afford to lose. The author is not responsible for any financial losses you may incur.


## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


## 🤝 Contributing
I'm genuinely excited to welcome contributors! 
Whether you're interested in refining the logging system, enhancing AI-prompt strategies, or enriching stock data — there’s room for your ideas and expertise. 
Feel free to submit pull requests or open issues with suggestions and improvements!


## 📧 Contact
If you have any questions or feedback, feel free to reach out at [goodbotty@proton.me](mailto:goodbotty@proton.me).
