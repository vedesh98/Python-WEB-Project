import os
import pandas as pd
import numpy as np
import talib as ta
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

# ---------------------------
# CONFIG
# ---------------------------
DATA_DIR = "/Users/umanggohil/Documents/BGYRT/dev-work/nifty500/maxdata"   # directory containing SYMBOL-data.csv
# DATA_DIR = "/Users/umanggohil/Documents/BGYRT/dev-work/General"
DATE_COL = "Date"
CAPITAL = 20_00_000   # 20 lakh
POSITION_SIZE = 2_00_000   # per trade
OUTPUT_DIR = "/Users/umanggohil/Documents/BGYRT/dev-work/General/onservations/symbol_trades_single"

RSI_VALUES = list(range(20, 75))   # 25 to 45
TRAIL_SL_PCTS = [ 0.05, 0.08, 0.10]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------
# BACKTEST ENGINE
# ---------------------------

def backtest(df, rsi_thresh, sl_pct):
    """Runs backtest for full data, returns trade list dataframe."""
    trades = []
    position = None  # {"entry_price": float, "stop": float, "qty": int, "entry_date": timestamp}
    positions = []
    cash = CAPITAL

    for i in range(1, len(df)):
        row_y = df.iloc[i-1]
        row = df.iloc[i]

        # Entry condition: RSI crosses above threshold
    #     if row_y["RSI"] < rsi_thresh <= row["RSI"]:
    #         entry_price = row["Close"]
    #         stop = entry_price * (1 - sl_pct)
    #         qty = POSITION_SIZE // entry_price
    #         if qty == 0:
    #             continue
    #         lv_position = {
    #             "entry_price": entry_price,
    #             "stop": stop,
    #             "qty": qty,
    #             "entry_date": row[DATE_COL]
    #         }
    #         positions.append(lv_position)
        
    #     for idx, position in enumerate(positions):
    #         position["stop"] = max(position["stop"], row["High"] * (1 - sl_pct))
    #         if row["Low"] <= position["stop"]:
    #             exit_price = position["stop"]
    #             pnl = (exit_price - position["entry_price"]) * position["qty"]
    #             trades.append({
    #                 "entry_date": position["entry_date"],
    #                 "exit_date": row[DATE_COL],
    #                 "entry_price": position["entry_price"],
    #                 "exit_price": exit_price,
    #                 "qty": position["qty"],
    #                 "pnl": pnl,
    #                 "rsi": rsi_thresh,
    #                 "sl_pct": sl_pct
    #             })
    #             cash += pnl
    #             del positions[idx]
            
    #         elif i == len(df) - 1:
    #             exit_price = row["Close"]
    #             pnl = (exit_price - position["entry_price"]) * position["qty"]
    #             trades.append({
    #                 "entry_date": position["entry_date"],
    #                 "exit_date": row[DATE_COL],
    #                 "entry_price": position["entry_price"],
    #                 "exit_price": exit_price,
    #                 "qty": position["qty"],
    #                 "pnl": pnl,
    #                 "rsi": rsi_thresh,
    #                 "sl_pct": sl_pct
    #             })
    #             cash += pnl
            
    # return pd.DataFrame(trades)

        # For single position at a time
        if position is None and row_y["RSI"] < rsi_thresh <= row["RSI"]:
            entry_price = row["Close"]
            stop = entry_price * (1 - sl_pct)
            qty = POSITION_SIZE // entry_price
            if qty == 0:
                continue
            position = {
                "entry_price": entry_price,
                "stop": stop,
                "qty": qty,
                "entry_date": row[DATE_COL]
            }

        # If in position -> check trailing stop & update stop
        if position is not None:
            # Update trailing stop
            position["stop"] = max(position["stop"], row["High"] * (1 - sl_pct))

            # Check stop hit
            if row["Low"] <= position["stop"]:
                exit_price = position["stop"]
                pnl = (exit_price - position["entry_price"]) * position["qty"]
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": row[DATE_COL],
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "qty": position["qty"],
                    "pnl": pnl,
                    "rsi": rsi_thresh,
                    "sl_pct": sl_pct
                })
                cash += pnl
                position = None

            # Or exit at last day
            elif i == len(df) - 1:
                exit_price = row["Close"]
                pnl = (exit_price - position["entry_price"]) * position["qty"]
                trades.append({
                    "entry_date": position["entry_date"],
                    "exit_date": row[DATE_COL],
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "qty": position["qty"],
                    "pnl": pnl,
                    "rsi": rsi_thresh,
                    "sl_pct": sl_pct
                })
                cash += pnl
                position = None

    return pd.DataFrame(trades)

# ---------------------------
# PROCESSING
# ---------------------------

def process_file(file):
    """Process a single stock file and save its trades as CSV."""
    if not file.endswith("-data.csv"):
        return None
    
    symbol = file.replace("-data.csv", "")
    path = os.path.join(DATA_DIR, file)
    out_path = os.path.join(OUTPUT_DIR, f"{symbol}_trades.csv")

    print(f"⚡ Running backtest for {symbol}...")

    df = pd.read_csv(path)
    if DATE_COL not in df.columns:
        print(f"❌ Skipping {symbol}, no {DATE_COL} column")
        return None

    # Clean + add RSI once
    df[DATE_COL] = pd.to_datetime(df[DATE_COL]).dt.tz_localize(None)
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()

    all_trades = []

    try:
        for rsi in RSI_VALUES:
            print(f"Processing {symbol} ... rsi :: {rsi}")
            for sl in TRAIL_SL_PCTS:
                trades_df = backtest(df, rsi, sl)
                if not trades_df.empty:
                    trades_df["symbol"] = symbol
                    all_trades.append(trades_df)

        if all_trades:
            final_df = pd.concat(all_trades, ignore_index=True)
            final_df.to_csv(out_path, index=False)
            print(f"✅ Saved trades for {symbol} -> {out_path}")
        else:
            print(f"ℹ️ No trades for {symbol}")

    except Exception as e:
        print(f"❌ Error {symbol}: {e}")
        return None


if __name__ == "__main__":
    files = [f for f in os.listdir(DATA_DIR) if f.endswith("-data.csv")]
    # files = ["NIFTY50-ONE_HOUR-data.csv"]

    cpu_cores = multiprocessing.cpu_count()
    max_workers = min(cpu_cores, len(files))

    print(f"🚀 Starting parallel backtests on {len(files)} files using {max_workers} workers...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_file, f): f for f in files}
        for future in as_completed(futures):
            _ = future.result()

    print(f"🎯 All symbol trade files saved in: {OUTPUT_DIR}")
