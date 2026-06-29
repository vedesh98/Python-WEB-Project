"""
Daily Stock RSI Analysis using Yahoo Finance (yfinance)
Replacement for Angel One API version
No API authentication needed, completely free!
"""
import pandas as pd
import requests
from datetime import datetime
import time
import os

# Try to import TA-Lib; if unavailable, provide a fallback implementation for RSI
try:
    import talib
except Exception:
    import numpy as np

    def _rsi_fallback(series, timeperiod=14):
        """
        Fallback RSI implementation compatible with talib.RSI signature.
        Accepts a pandas Series or array-like and returns a numpy array.
        Uses Wilder's smoothing via exponential moving average.
        """
        # Convert to pandas Series if needed
        if isinstance(series, (list, tuple, np.ndarray)):
            ser = pd.Series(series)
        else:
            ser = series.copy()

        # Calculate differences
        delta = ser.diff()

        # Separate gains and losses
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)

        # Wilder's smoothing (exponential moving average with alpha=1/period)
        ma_up = up.ewm(alpha=1.0 / timeperiod, adjust=False).mean()
        ma_down = down.ewm(alpha=1.0 / timeperiod, adjust=False).mean()

        # Avoid division by zero
        rs = ma_up / ma_down.replace(0, np.nan)

        rsi = 100 - (100 / (1 + rs))

        # Return numpy array to mimic talib behavior
        return rsi.values

    class _TalibFallback:
        RSI = staticmethod(_rsi_fallback)

    talib = _TalibFallback()

import yfinance as yf
from logzero import logger
from dotenv import load_dotenv

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

# Static values
window = 965  # Days of historical data

# API credentials (Telegram only, no trading API needed)
bot_token = os.environ.get("BOT_TOKEN")
test_mode = os.environ.get("TEST_MODE", "false").lower() == 'true'

# Get dates
todays_date = (datetime.today() - pd.DateOffset(days=2)).strftime("%Y-%m-%d")
window_date = (datetime.today() - pd.DateOffset(days=window)).strftime("%Y-%m-%d")

print(f"📊 Daily Stock Analysis")
print(f"Analysis Date: {todays_date}")
print(f"Window: {window_date} to {todays_date}")
print("=" * 70)

# ============================================
# LOAD STOCK LIST
# ============================================

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "Main_df.csv")

try:
    main_df = pd.read_csv(file_path)
    print(f"✓ Loaded {len(main_df)} stocks from Main_df.csv")
except FileNotFoundError:
    print(f"✗ Error: Main_df.csv not found in {current_dir}")
    print("Please create Main_df.csv with columns: Symbol, token, rsi, priority, win_ratio")
    exit(1)

# ============================================
# DATA FETCHING FUNCTIONS (yfinance)
# ============================================

def fetch_candle_data_yfinance(symbol, interval='1d'):
    """
    Fetch daily candle data from Yahoo Finance
    
    Parameters:
    - symbol: Stock symbol (without .NS, we'll add it)
    - interval: Data interval ('1d' for daily)
    
    Returns:
    - List of [Date, Open, High, Low, Close, Volume]
    """
    period = '1y'  # Fetch 1 year of data for RSI calculation
    try:
        # Add .NS suffix for NSE stocks
        ticker_symbol = f"{symbol}.NS"


        df = yf.Ticker(ticker_symbol).history(period=period, interval=interval)
        df['RSI_14'] = talib.RSI(df['Close'], timeperiod=14)
        df.reset_index(inplace=True)
        
        if df.empty:
            logger.error(f"No data found for {symbol}")
            return None
        
        # Reset index to make Date a column
        df = df.reset_index()
        
        
        return df
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def fetch_candle_week_month_data(symbol, daily_json_data=None):
    """
    Calculate weekly/monthly candles from daily data
    
    Parameters:
    - symbol: Stock symbol
    - range: 'W' for weekly, 'ME' for monthly
    - daily_json_data: Daily data (if available)
    
    Returns:
    - DataFrame with weekly/monthly OHLCV and RSI
    """
    period = '3y'
    
    try:
        if daily_json_data is None:
            daily_json_data = fetch_candle_data_yfinance(symbol, interval='1mo', period=period)
        
        if daily_json_data is None:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(daily_json_data, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        
        # Convert Date to datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        
        # Set Date as index for resampling
        df.set_index('Date', inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating {range} data for {symbol}: {e}")
        return None


# ============================================
# RSI ANALYSIS FUNCTIONS
# ============================================

def rsi_trend1(rsi_values, setup_rsi):
    """
    Determine RSI trend direction
    """
    try:
        if rsi_values[-1] >= 60 and rsi_values[-2] < 60:
            return "60 CROSSOVER"
        
        if rsi_values[-1] >= setup_rsi and rsi_values[-2] < setup_rsi:
            return setup_rsi + 1
        
        if rsi_values[-1] < setup_rsi and rsi_values[-2] >= setup_rsi:
            return setup_rsi - 1
        
        if rsi_values[-1] > rsi_values[-2]:
            return 'UP'
        else:
            return 'DOWN'
    except:
        return None


def rsi_trend(rsi_values, setup_rsi):
    """
    Check if RSI crossed above setup threshold
    """
    print('RSI Values:', rsi_values, 'Setup RSI:', setup_rsi)
    try:
        if rsi_values[-1] >= setup_rsi and rsi_values[-2] < setup_rsi:
            # print(f"✓ RSI crossed above setup threshold: {setup_rsi}")
            return True
    except:
        # print("Error in rsi_trend function")
        pass
        
    return False


def rsi_trend_P1(rsi_values, setup_rsi):
    """
    Check if RSI is near setup threshold (within ±5)
    """
    try:
        if (setup_rsi - 5) <= rsi_values[-1] <= (setup_rsi + 5):
            return True
    except:
        pass
    return False


# ============================================
# TELEGRAM FORMATTING FUNCTIONS
# ============================================

def format_whatsapp_report(data, name):
    """Format report for Telegram"""
    
    if len(data) == 0:
        lines = [f"📊 <b>{name} : 0 Stocks </b>"]
    else:
        lines = [f"📊 <b>{name}</b>"]
        for index, item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1}. {item['Name']}</b>"
                f"\n   <b>Today's RSI:</b> {item['Daily_RSI']:.2f}"
                f"\n   <b>Yesterday's RSI:</b> {item['yesterday_RSI']:.2f}"
                f"\n   <b>Setup RSI:</b> {item['Setup_RSI']:.2f}"
            )
    
    return "\n".join(lines)


def format_whatsapp_error(data, name):
    """Format error report for Telegram"""
    
    lines = [f"📊 <b>{name}</b>"]
    
    if len(data) == 0:
        lines.append("\n🔹 <b>No Errors</b>")
    else:
        for index, item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1}. {item['Name']}</b>"
                f"\n   <b>Setup RSI:</b> {item['Setup_RSI']:.2f}"
                f"\n   <b>Reason:</b> {item['reason']}"
            )
    
    return "\n".join(lines)


def format_whatsapp_40_report(data, name):
    """Format RSI 40 crossover report for Telegram"""
    
    if len(data) == 0:
        lines = [f"📊 <b>{name} : 0 Stocks </b>"]
    else:
        lines = [f"📊 <b>{name}</b>"]
        for index, item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1}. {item['Name']}</b>"
                f"\n   <b>Current Month RSI:</b> {item['Monthly_RSI']:.2f}"
                f"\n   <b>Last Month RSI:</b> {item['last_Month_RSI']:.2f}"
                f"\n   <b>Priority:</b> {item['Priority']}"
            )
    
    return "\n".join(lines)


# ============================================
# SEND TELEGRAM MESSAGES
# ============================================

def send_telegram_message(message, chat_id=None, is_test=False):
    """Send message to Telegram"""
    
    if not bot_token:
        logger.warning("⚠️  BOT_TOKEN not set")
        return False
    
    try:
        if is_test:
            test_id = "529251493"
            chat_id = test_id
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.get(url, params=params, timeout=5)
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False


# ============================================
# MAIN PROCESSING
# ============================================

# Initialize output containers
output_data = []
error_data = []
priority_data = []
priority_watch_data = []
priority0_data = []
rsi_40_cross_data = []

print("\n📈 Processing Stocks...")
print("=" * 70)

# Process each stock
for idx, (_, row) in enumerate(main_df.iterrows(), 1):
    
    time.sleep(2)  # Rate limiting
    
    priority = row['priority']
    name = row['Symbol']
    token = row['token']
    rsi = row['rsi']
    win_ratio = row['win_ratio']
    
    try:
        # Check if RSI is defined
        if pd.isna(rsi) or rsi is None:
            error_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'reason': 'RSI not maintained in file'
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ✗ RSI not defined")
            continue
        
        # Fetch daily data
        daily_json_data = fetch_candle_data_yfinance(name)
        
        if daily_json_data is None:
            error_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'reason': 'Error while fetching data from Yahoo Finance'
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ✗ No data")
            continue
        
        # Fetch monthly data
        # monthly_data = fetch_candle_week_month_data(name)
        
        # print(monthly_data)
        # Get last 2 monthly RSI values
        # last_2_rsi_monthly = monthly_data['RSI_14'].dropna().tail(2).values
        
        # if len(last_2_rsi_monthly) < 2:
        #     error_data.append({
        #         'Name': name,
        #         'Setup_RSI': rsi,
        #         'reason': 'Not enough monthly RSI data'
        #     })
        #     print(f"[{idx}/{len(main_df)}] {name:<15} ✗ Insufficient monthly data")
            
        # else:
        #     print(f"[{idx}/{len(main_df)}] {name:<15} ✓ Monthly RSI: {last_2_rsi_monthly[-1]:.2f}, Last Month RSI: {last_2_rsi_monthly[-2]:.2f}")
        #     # Check for RSI 40 crossover
        #     if last_2_rsi_monthly[-2] <= 40 or last_2_rsi_monthly[-1] <= 40:
        #         rsi_40_cross_data.append({
        #             'Name': name,
        #             'Monthly_RSI': last_2_rsi_monthly[-1],
        #             'last_Month_RSI': last_2_rsi_monthly[-2],
        #             'Priority': priority,
        #         })
        
        # Process daily data
        df = daily_json_data.copy()

        df['Date'] = pd.to_datetime(df['Date'])
        
        df = df.sort_values('Date').reset_index(drop=True)
        
        
        
        # Get last 2 daily RSI values
        last_2_rsi_daily = df['RSI_14'].iloc[-2:].values

       
        
        if len(last_2_rsi_daily) < 2:
            error_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'reason': 'Not enough daily RSI data'
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ✗ Insufficient daily data")
            continue
        
        daily_rsi = last_2_rsi_daily[-1]
        yesterday_rsi = last_2_rsi_daily[-2]

        last_date = pd.to_datetime(df["Date"].iloc[-1]).strftime('%Y-%m-%d')

        
        # Check if data is up to date
        if last_date != todays_date:
            error_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'reason': f'Last data: {last_date}, Expected: {todays_date}'
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ⚠️  Data date mismatch ({last_date})")
            continue
        
        # Check for setup based on priority
        if priority == 2:
            if rsi_trend(last_2_rsi_daily, rsi):
                priority_data.append({
                    'Name': name,
                    'Setup_RSI': rsi,
                    'Daily_RSI': daily_rsi,
                    'yesterday_RSI': yesterday_rsi,
                    'win_ratio': win_ratio,
                })
                print(f"[{idx}/{len(main_df)}] {name:<15} ✓ SETUP (P2) | RSI: {daily_rsi:.2f}")
                continue
            
            if rsi_trend_P1(last_2_rsi_daily, rsi):
                priority_watch_data.append({
                    'Name': name,
                    'Setup_RSI': rsi,
                    'Daily_RSI': daily_rsi,
                    'yesterday_RSI': yesterday_rsi,
                    'win_ratio': win_ratio,
                })
                print(f"[{idx}/{len(main_df)}] {name:<15} ⚠  WATCH (P2) | RSI: {daily_rsi:.2f}")
                continue
        
        elif priority == 1 and rsi_trend(last_2_rsi_daily, rsi):
            output_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'Daily_RSI': daily_rsi,
                'yesterday_RSI': yesterday_rsi,
                'win_ratio': win_ratio,
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ✓ SETUP (P1) | RSI: {daily_rsi:.2f}")
        
        elif priority == 0 and rsi_trend(last_2_rsi_daily, rsi):
            priority0_data.append({
                'Name': name,
                'Setup_RSI': rsi,
                'Daily_RSI': daily_rsi,
                'yesterday_RSI': yesterday_rsi,
                'win_ratio': win_ratio,
            })
            print(f"[{idx}/{len(main_df)}] {name:<15} ✓ SETUP (P0) | RSI: {daily_rsi:.2f}")
        else:
            print(f"[{idx}/{len(main_df)}] {name:<15}   No setup | RSI: {daily_rsi:.2f}")
    
    except Exception as e:
        error_data.append({
            'Name': name,
            'Setup_RSI': rsi,
            'reason': str(e)
        })
        print(f"[{idx}/{len(main_df)}] {name:<15} ✗ Error: {e}")

# ============================================
# SEND TELEGRAM REPORTS
# ============================================

print("\n" + "=" * 70)
print("📤 Sending Telegram Reports...")
print("=" * 70)

TEST_ID = "529251493"
CHAT_ID = TEST_ID if test_mode else os.environ.get("CHAT_ID", TEST_ID)

# Main report
msg_header = f"📊 <b>Daily Report: {todays_date}</b>\n\n⏰ <i>Data from Yahoo Finance (15-min delayed)</i>"
print(msg_header)
send_telegram_message(msg_header, CHAT_ID)
time.sleep(1)

# Priority 2 stocks
msg_p1 = format_whatsapp_report(priority_data, 'Priority 2 Stocks (Setup)')
send_telegram_message(msg_p1, CHAT_ID)
time.sleep(1)

# Priority 2 watch stocks
msg_p2 = format_whatsapp_report(priority_watch_data, 'Priority 2 Stocks (Watch)')
send_telegram_message(msg_p2, CHAT_ID)
time.sleep(1)

# Trading stocks
msg_t = format_whatsapp_report(output_data, 'Priority 1 Trading Stocks')
send_telegram_message(msg_t, CHAT_ID)
time.sleep(1)

# Priority 0 stocks
msg_p0 = format_whatsapp_report(priority0_data, 'Priority 0 Stocks')
send_telegram_message(msg_p0, CHAT_ID)
time.sleep(1)

# Error report (to test ID)
if len(error_data) > 0:
    error_msg = format_whatsapp_error(error_data, 'Error Stocks')
    send_telegram_message(error_msg, TEST_ID)
    print(f"✓ Sent error report with {len(error_data)} stocks")
    time.sleep(1)

# RSI 40 crossover report
msg_40 = format_whatsapp_40_report(rsi_40_cross_data, 'RSI 40 Crossover Stocks')
send_telegram_message(msg_40, TEST_ID)

# ============================================
# SUMMARY
# ============================================

print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"Priority 2 (Setup):     {len(priority_data)} stocks")
print(f"Priority 2 (Watch):     {len(priority_watch_data)} stocks")
print(f"Priority 1 (Trading):   {len(output_data)} stocks")
print(f"Priority 0:             {len(priority0_data)} stocks")
print(f"RSI 40 Crossover:       {len(rsi_40_cross_data)} stocks")
print(f"Errors:                 {len(error_data)} stocks")
print("=" * 70)
print("✅ Analysis complete!")
print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
