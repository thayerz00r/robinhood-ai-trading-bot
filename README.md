# Robinhood Trading Bot

This is an automated trading bot for Robinhood that makes buy, sell, or hold decisions based on moving averages and insights from OpenAI. The bot processes stocks in your portfolio and watchlists, making decisions and executing trades accordingly.

## Features

- Automated trading based on moving averages
- Integration with OpenAI for enhanced decision-making
- Processes stocks in your portfolio and watchlists
- Configurable buying and selling parameters

## Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/siropkin/robinhood-trading-bot.git
    cd robinhood-trading-bot
    ```

2. **Install dependencies:**

    ```sh
    pip install robin_stocks pandas numpy
    ```

3. **Fill global variables in the bot file:**

    You can configure the bot by modifying the global variables in `main.py`:
    - `OPENAI_API_KEY`: OpenAI API key
    - `ROBINHOOD_USERNAME`: Robinhood username is the email address used for login
    - `ROBINHOOD_PASSWORD`: Robinhood password is not the same as the login password
    - `WATCHLIST_NAMES`: Watchlist names to get stocks from
    - `BUYING_AMOUNT_PERCENTAGE`: Default percentage of buying power that will be used for buying stocks, for example if buying power is 1000$ and BUYING_AMOUNT_PERCENTAGE = 0.25, then 250$ will be used for buying stocks
    - `MIN_BUYING_AMOUNT_USD`: Minimum amount to buy in dollars
    - `MAX_BUYING_AMOUNT_USD`: Maximum amount to buy in dollars
    - `SELLING_AMOUNT_PERCENTAGE`: Default percentage of holding that will be sold at once, for example if holding is 100 stocks and SELLING_AMOUNT_PERCENTAGE = 0.25, then 25 stocks will be sold at once

## Usage

1. **Run the trading bot:**

    ```sh
    python main.py
    ```

## Disclaimer

This bot is for educational purposes only. Trading stocks involves risk, and you should only trade with money you can afford to lose. The author is not responsible for any financial losses you may incur.


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
