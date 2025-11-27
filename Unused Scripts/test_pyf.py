import glob
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import pandas as pd



# Folder containing CSV files
FOLDER_PATH = "test_fol"
rsi_column = "RSI_14"


# -----------------------------
# CHECK PROFIT/LOSS FUNCTION
# -----------------------------
def check_profit_loss(df, start_index):
    entry_price = df.loc[start_index, "Close"]
    target_profit = entry_price * 1.01     # +1%
    target_loss   = entry_price * 0.99     # -1%

    future = df.loc[start_index+1:]
    curr_date = pd.to_datetime(df.loc[start_index, "Date"]).strftime("%Y-%m-%d")

    for idx, row in future.iterrows():
        high = row["High"]
        low = row["Low"]
        date_ind = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
        if date_ind != curr_date:
            break

        if low <= target_loss:
            return "LOSS"

        if high >= target_profit:
            return "WIN"

    return "NO_RESULT" 


# -----------------------------
# PROCESS SINGLE CSV FILE
# -----------------------------
def process_single_rsi(df, file_name, rsi_value):
            local_results = []
            matching_rows = df[df[rsi_column] == rsi_value]

            for index in matching_rows.index:
                result = check_profit_loss(df, index)
                local_results.append({
                    "file": file_name,
                    "rsi": rsi_value,
                    "index": index,
                    "result": result
                })
            return local_results
        
        
def process_file(file_path):
    file_name = os.path.basename(file_path)

    try:
        df = pd.read_csv(file_path)

        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["High"]  = pd.to_numeric(df["High"], errors="coerce")
        df["Low"]   = pd.to_numeric(df["Low"], errors="coerce")
        df[rsi_column] = pd.to_numeric(df[rsi_column], errors="coerce")

        df.dropna(subset=["Close", "High", "Low", rsi_column], inplace=True)

        results_local = []
        # rsi_values = sorted(df[rsi_column].unique())
        rsi_values = [21.4]
        print(rsi_values)
        
        
        workers = max(1, os.cpu_count() // 2)
        print(f"Using {workers} workers for RSI processing.")
                    
        with ProcessPoolExecutor(max_workers=workers) as tpool:
            # inner_futures = tpool.map(process_single_rsi, rsi_values)
            inner_futures = {tpool.submit(process_single_rsi, df, file_name, rsi_value): rsi_value for rsi_value in rsi_values}

        # Combine all returned results
            # time.sleep(100)
            # wait(inner_futures)
            for future in as_completed(inner_futures):
                file = inner_futures[future]
                try:
                    result = future.result()
                    # results_local.extend(result)
                    print(f"Finished: {file}")
                except Exception as e:
                    print(f"Error in {file}: {e}")
        
        
        print(future)
        print(f"Completed processing {file_name}")

        return results_local

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        return []


values = process_file('test_fol/Final_5min_RSI_CIPLA_from_2025-01-01_to_2025-11-19.csv')

print(values)