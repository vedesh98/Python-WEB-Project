import pandas as pd
import numpy as np
import time

FOLDER_PATH = "5min data"
rsi_column = "RSI_14"


def check_profit_loss_fast(df, start_index, end_index):
    """Vectorized profit/loss scan (NO LOOPS)"""
    entry_price = df["Close"][start_index]
    target_profit = entry_price * 1.01
    target_loss = entry_price * 0.99
    quantity = int(100000 / entry_price)
    date = df["Date"].loc[start_index]
    future = df.iloc[start_index + 1 : end_index + 1]
    high = future["High"].values
    low = future["Low"].values

    # profit/loss 
    if len(high) > 0 and len(low) > 0:    
        hit_profit = np.argmax(high >= target_profit) 
        hit_loss = np.argmax(low <= target_loss)
    # print(hit_profit, hit_loss)
    # print(len(high), len(low),date)
        if high[hit_profit] >= target_profit:
            exit_price = target_profit
            exit_index = start_index + 1 + hit_profit
        elif low[hit_loss] <= target_loss:
            exit_price = target_loss
            exit_index = start_index + 1 + hit_loss
        else:
            # exit at 15:25 or last candle
            exit_index = start_index + 1
            exit_price = df["Close"].iloc[exit_index]
    else:
        # print(len(high), len(low), date)
        # print("Error at index:", start_index, entry_price, "date:", date)
        exit_index = end_index
        exit_price = df["Close"].iloc[exit_index]
        
        

    # result = quantity * (exit_price - entry_price)
    result = ( exit_price - entry_price ) / entry_price * 100  # return percentage

    return result, exit_index, exit_price, entry_price, quantity, date


def check_rsi_fast(df, rsi_value):
    r = df[rsi_column].values
    crossed = np.where((r[:-1] < rsi_value) & (r[1:] >= rsi_value))[0] + 1

    results = []
    for idx in crossed:
        date_entry = df["Date"].iloc[idx][:10]
        end_idx = df.index[df["Date"].str.startswith(date_entry)].max()
        # print("Processing RSI:", rsi_value, "at index:", idx, "end index:", end_idx)
        result, exit_index, exit_price, entry_price, qty, date = check_profit_loss_fast(df, idx, end_idx)
        results.append({
            "rsi": rsi_value,
            "index_cross_rsi": idx,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "Date_entry": date_entry,
            "quantity": qty,
            # "Date_Exit": ,
            "exit_index": end_idx,
            "result": result
        })

    return results



def optimized_summary(results_df):
    # Convert columns to arrays (fastest)
    rsi_arr = results_df["rsi"].values
    result_arr = results_df["result"].values

    # Encode results as numbers for fast bincount
    # WIN = 1, LOSS = 2, NO_RESULT = 0
    encode_map = {"NO_RESULT": 0, "WIN": 1, "LOSS": 2}
    result_encoded = np.vectorize(encode_map.get)(result_arr)
    
    # Unique RSI values
    unique_rsi = np.unique(rsi_arr)

    # Prepare arrays for summary
    win_counts = np.zeros(len(unique_rsi), dtype=int)
    loss_counts = np.zeros(len(unique_rsi), dtype=int)
    no_counts = np.zeros(len(unique_rsi), dtype=int)

    # Pre-build a map: RSI → row index in summary arrays
    rsi_to_idx = {r: i for i, r in enumerate(unique_rsi)}

    # Use bincount grouped by RSI values
    for rsi_value in unique_rsi:
        mask = (rsi_arr == rsi_value)
        counts = np.bincount(result_encoded[mask], minlength=3)

        no_counts[rsi_to_idx[rsi_value]]   = counts[0]  # NO_RESULT
        win_counts[rsi_to_idx[rsi_value]]  = counts[1]  # WIN
        loss_counts[rsi_to_idx[rsi_value]] = counts[2]  # LOSS

    # Total trades
    total = win_counts + loss_counts
    win_ratio = np.where(total == 0, 0, (win_counts / total * 100).round(2))

    # Build final df
    summary_df = pd.DataFrame({
        "rsi": unique_rsi,
        "WIN": win_counts,
        "LOSS": loss_counts,
        "NO_RESULT": no_counts,
        "total_trades": total,
        "win_ratio_percent": win_ratio
    })

    return summary_df



def process_file_fast(path):
    df = pd.read_csv(path)
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["High"]  = pd.to_numeric(df["High"], errors="coerce")
    df["Low"]   = pd.to_numeric(df["Low"], errors="coerce")
    df[rsi_column] = pd.to_numeric(df[rsi_column], errors="coerce")
    df.dropna(subset=["Close", "High", "Low", rsi_column], inplace=True)
    df = df.reset_index(drop=True)

    all_results = []
    for rsi_value in range(10, 90,1):
        all_results.extend(check_rsi_fast(df, rsi_value))

    return pd.DataFrame(all_results)


if __name__ == "__main__":
    t0 = time.time()
    df_out = process_file_fast(
        "c:/Users/admin/project/BGRYT/Python-WEB-Project/test_fol/Final_5min_RSI_ZEEL_from_2025-01-01_to_2025-11-19.csv"
    )
    df_out.to_csv("FAST_OUTPUT2.csv", index=False)
    print("Execution Time:", time.time() - t0)
    print(df_out)