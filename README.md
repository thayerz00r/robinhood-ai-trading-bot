# Robinhood Trading Bot

This is an automated trading bot for Robinhood that makes buy, sell, or hold decisions based on moving averages and insights from OpenAI. The bot processes stocks in your portfolio and watchlists, making decisions and executing trades accordingly.

## Features

- Automated trading based on moving averages
- Integration with OpenAI for enhanced decision-making
- Processes stocks in your portfolio and watchlists
- Configurable buying and selling parameters

## How It Works

1. **Execution Interval:**
   - The bot runs every set number of seconds, as defined by `RUN_INTERVAL_SECONDS`.

2. **Stock Processing:**
   - The bot takes the current available stocks in your portfolio and tries to make decisions based on moving averages and insights from OpenAI.
   - It also processes stocks from your watchlists and makes decisions accordingly.

3. **Decision Making:**
   - For each stock, the bot decides whether to buy, sell, or hold based on predefined criteria and market data.

4. **Error Handling:**
   - Any errors encountered during processing are logged with a timestamp for debugging purposes.

## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/siropkin/robinhood-trading-bot.git
    cd robinhood-trading-bot
    ```

2. **Install dependencies:**

    ```sh
    pip install robin_stocks openai pandas
    ```

3. **Configure the bot:**

   You can configure the bot by modifying the global variables in `config.py`:
   - `MODE` - Trading mode (demo, auto, manual)
   - `RUN_ON_WORKDAYS_ONLY` - Run bot only on workdays
   - `RUN_INTERVAL_SECONDS` - Trading interval in seconds
   - `WATCHLIST_NAMES` - Watchlist names (can be empty, or "My First List", "My Second List", etc.)
   - `WATCHLIST_OVERVIEW_LIMIT` - Number of stocks to process in decision-making (e.g. 20)
   - `OPENAI_MODEL_NAME` - OpenAI model name
   - `MIN_SELLING_AMOUNT_USD` - Minimum sell amount in USD
   - `MAX_SELLING_AMOUNT_USD` - Maximum sell amount in USD
   - `MIN_BUYING_AMOUNT_USD` - Minimum buy amount in USD
   - `MAX_BUYING_AMOUNT_USD` - Maximum buy amount in USD
   - `OPENAI_API_KEY` - OpenAI API key
   - `ROBINHOOD_USERNAME` - Robinhood username
   - `ROBINHOOD_PASSWORD` - Robinhood password

## Usage

1. **Run the trading bot:**

    ```sh
    python main.py
    ```

## Disclaimer

This bot is for educational purposes only. Trading stocks involves risk, and you should only trade with money you can afford to lose. The author is not responsible for any financial losses you may incur.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
