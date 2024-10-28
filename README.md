![Jay and Silent Bob](jay_and_silent_bob.png)

Fuck, fuck, fuck, motherfuck,<br />
Rollin' stocks, makin' trades,<br />
Time to cash in, watch those gains

# 🚀 Robinhood Trading Bot 🤖
Welcome to the **Robinhood Trading Bot**! This Python script integrates with the Robinhood trading platform and OpenAI to automate stock trading decisions based on your portfolio and watchlist.

## 📦 Features
- **Automated Trading Decisions**: Leverages AI to analyze your portfolio and make buy/sell recommendations.
- **Watchlist Integration**: Monitor stocks on your watchlist and make informed decisions.
- **Configurable Modes**: Run the bot in demo, manual, or auto mode.
- **Post-Decision Adjustments**: The bot can refine its decisions based on trading results.

## 📊 Decision-Making System And Post-Decision Adjustments
The bot's decision-making system incorporates various analytical components to enhance trading accuracy:
1. **Average Price Analytics**: The bot evaluates historical price trends and moving averages to determine optimal buy and sell points.
2. **Robinhood Analyst Ratings**: The system analyzes stock ratings from Robinhood, considering both bullish and bearish perspectives to inform decisions. This helps identify market sentiment and potential price movements.
3. **OpenAI Integration**: Utilizes AI for comprehensive analysis of stock performance and trading opportunities, optimizing decision-making based on portfolio and market data.
4. **Configurable Parameters**: The bot allows users to set specific thresholds and conditions for trading actions, ensuring personalized strategy alignment.
5. **Post-Decision Adjustments**: After executing trades, the bot can adjust its decisions based on the trading results. This post-decision adjustment feature enables the bot to refine its strategies and adapt to market conditions effectively.

## ⚙️ Configuration Parameters
```python
# Credentials
OPENAI_API_KEY = "..."                  # OpenAI API key
ROBINHOOD_USERNAME = "..."              # Robinhood username
ROBINHOOD_PASSWORD = "..."              # Robinhood password

# Basic config parameters
MODE = "demo"                           # Trading mode (demo, auto, manual)
RUN_ON_WORKDAYS_ONLY = True             # Run bot only on workdays
RUN_INTERVAL_SECONDS = 600              # Trading interval in seconds

# Robinhood config parameters
WATCHLIST_NAMES = []                    # Watchlist names (can be empty, or "My First List", "My Second List", etc.)
WATCHLIST_OVERVIEW_LIMIT = 10           # Number of stocks to process in decision-making (e.g. 20)
PAUSE_BETWEEN_REQUESTS = 0.1            # Pause between Robinhood API requests in seconds to avoid rate limiting

# OpenAI config params
MAKE_POST_DECISION_ADJUSTMENTS = True   # Make adjustments to the decision after the decision is made based on the trading results
MAX_POST_DECISION_ADJUSTMENTS = 1       # Maximum number of adjustments to make
OPENAI_MODEL_NAME = "gpt-4o-mini"       # OpenAI model name

# Trading parameters
MIN_SELLING_AMOUNT_USD = 1.0            # Minimum sell amount in USD
MAX_SELLING_AMOUNT_USD = 10.0           # Maximum sell amount in USD
MIN_BUYING_AMOUNT_USD = 1.0             # Minimum buy amount in USD
MAX_BUYING_AMOUNT_USD = 10.0            # Maximum buy amount in USD
```

## 🔑 Installation
1. Clone the repository:
    ```sh
    git clone https://github.com/siropkin/robinhood-trading-bot.git
    cd robinhood-trading-bot
    ```

2. Install dependencies:
    ```sh
    pip install robin_stocks openai pandas numpy
    ```

3. Clone `config.py.example` to `config.py` and fill in the required parameters:
    ```sh
    cp config.py.example config.py
    ```

## 📈 How to Run
To start the bot, run the following command in your terminal:
   ```sh
   python main.py
   ```

## 💬 How It Works
1. Login to OpenAI: The bot logs into OpenAI using your API key.
2. Login to Robinhood: The bot logs into your Robinhood account using your credentials.
3. Fetch Stocks: It retrieves your current stock holdings and watchlist stocks.
4. AI Analysis: Using OpenAI, it analyzes your portfolio and watchlist to make informed trading decisions.
5. Execute Trades: Based on the AI's recommendations, the bot will execute buy/sell orders.
6. Post-Decision Adjustments: The bot can adjust its decisions based on the outcome of the trades.


## ⚠️ Disclaimer
This bot is for educational purposes only. Trading stocks involves risk, and you should only trade with money you can afford to lose. The author is not responsible for any financial losses you may incur.

## 📄 License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🤝 Contributing
Feel free to submit pull requests or open issues if you have suggestions or improvements!


## 📧 Contact

If you have any questions or feedback, feel free to reach out at [ivan.seredkin@gmail.com](mailto:ivan.seredkin@gmail.com).


## 📈
Happy Trading! 💰📈

