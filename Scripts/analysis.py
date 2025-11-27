import glob
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import pandas as pd
import numpy as np

# Folder containing CSV files
FOLDER_PATH = "5min data"
rsi_column = "RSI_14"


# -----------------------------
# CHECK PROFIT/LOSS FUNCTION
# -----------------------------
def check_profit_loss(df, start_index, percentage_move=1):
    end_time = "15:25:00"
    investment_amount = 100000  # Fixed investment amount per trade
    entry_price = df.loc[start_index, "Close"]
    target_profit = entry_price * (100 + percentage_move) / 100     # +1%
    target_loss   = entry_price * (100 - percentage_move) / 100     # -1%
    
    quantity = int(investment_amount / entry_price)
    invested_amount = quantity * entry_price
    

    future = df.loc[start_index+1:]
    curr_date = pd.to_datetime(df.loc[start_index, "Date"]).strftime("%Y-%m-%d")
    # print(os.cpu_count())
    for idx, row in future.iterrows():
        high = row["High"]
        low = row["Low"]
        date_ind = pd.to_datetime(row["Date"]).strftime("%Y-%m-%d")
        time_ind = pd.to_datetime(row["Date"]).strftime("%H:%M:%S")
        if time_ind == end_time or date_ind != curr_date:
            exit_price = row["Close"]
            break

        if low <= target_loss:            
            exit_price = target_loss
            break

        if high >= target_profit:
            exit_price = target_profit
            break
                
    return { 
            "invested_amount": invested_amount,
            "quantity": quantity,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "index": idx,
            "entry_time": df.loc[start_index, "Date"],
            "exit_time": row["Date"],
            "pnl": quantity * ( exit_price - entry_price) ,
            "percentage_move": percentage_move,
            # "result": ,
                    }


# def check_rsi(df, rsi_value):
def check_rsi(df, rsi_value):

    r = df[rsi_column].values
    crossed = np.where((r[:-1] < rsi_value) & (r[1:] >= rsi_value))[0] + 1
    available_threads = 3 
    #os.cpu_count() or 1
    results = []
    profit_percentage_moves = [0.5, 1, 1.5, 2]
    
    for i in profit_percentage_moves:
        for idx in crossed:
            out = check_profit_loss(df, idx, percentage_move=i)
            out["rsi"] = rsi_value
            results.append(out)

    return results


def process_file(file_path):
    file_name = os.path.basename(file_path)
    token = file_name.split('_')[3]
    # file_name = file_path

    try:
        df = pd.read_csv(file_path)

        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df["High"]  = pd.to_numeric(df["High"], errors="coerce")
        df["Low"]   = pd.to_numeric(df["Low"], errors="coerce")
        df[rsi_column] = pd.to_numeric(df[rsi_column], errors="coerce")

        df.dropna(subset=["Close", "High", "Low", rsi_column], inplace=True)
        #reset the index
        df = df.reset_index(drop=True)
        # print(df)
        results_local = []
        # #take rsi_column values which are multiple duplicates more then 10 times
        rsi_values = range(10,91,1)
        

        #check available threads
        available_threads = min( os.cpu_count() or 1, len(rsi_values) ) 
        print(f"Available CPU threads: {available_threads}")

        
        
        all_results = []
        #  convert below code into paralallel processing
        
        with ProcessPoolExecutor(max_workers=available_threads) as executor:
        # with ThreadPoolExecutor(max_workers=available_threads) as executor:
            futures = {executor.submit(check_rsi, df, rsi_value): rsi_value for rsi_value in rsi_values}    
            
            for fut in as_completed(futures):
                f = futures[fut]
                try:
                    res = fut.result()
                    if res:
                        all_results.extend(res)
                        
                    print(f"Completed RSI {f}: {len(res)} results")
                except Exception as e:
                    print(f"Error processing RSI {f} in {file_name}: {e}")
                # Loop for each RSI value
                # for rsi_value in rsi_values:
                    
                #     results_local.append(check_rsi(df, rsi_value))
                
            summary_df = pd.DataFrame(all_results)
            # summary_df[rsi_column]
            # summary_df[rsi_column] = pd.to_numeric(summary_df[rsi_column], errors="coerce").round(2)
            # create file csv with details
            summary_df = summary_df.sort_values(by=["rsi", "index"])
            # summary_df["exit_price"].to_string()  
            # summary_df["entry_price"].to_string()
            # summary_df["invested_amount"].to_string()
            # summary_df["quantity"].to_string()
            # # summary_df["result"].to_string()    
            # summary_df["rsi"].to_string()
            # summary_df["index"].to_string() 
            print(file_name)
        #create file without file column
        # summary_df = summary_df.drop(columns=["file"])
            summary_df.to_csv(f'c:/Users/admin/project/BGRYT/Python-WEB-Project/treads/{token}_Treads.csv', index=False)
        
        # return results_local

    except Exception as e:
        print(f"Error processing {file_name}: {e}")
        return []



if __name__ == "__main__":
    # start_time = time.time()

    # all_results = []

    # for file_path in csv_files:
    #     results = process_file(file_path)
    #     all_results.extend(results)

    # end_time = time.time()
    # print(f"Processed {len(csv_files)} files in {end_time - start_time:.2f} seconds.")

    # # Example: Print first 5 results
    # for res in all_results[:5]:
    #     print(res)


    start_time = time.perf_counter()
    
    FOLDER_PATH = 'c:/Users/admin/project/BGRYT/Python-WEB-Project/5min data'

    csv_files = glob.glob(os.path.join(FOLDER_PATH, "*.csv"))
    print(f"Found {len(csv_files)} CSV files.")
    

    
    for file_path in csv_files:
        process_file(file_path)
    
    
    # with ProcessPoolExecutor() as executor:
    #     futures = {executor.submit(process_file, file_path): file_path for file_path in csv_files}
        
    #     for fut in as_completed(futures):
    #         file_path = futures[fut]
    #         try:
    #             fut.result()
    #             print(f"Completed processing {file_path}")
    #         except Exception as e:
    #             print(f"Error processing {file_path}: {e}")

    # Your Python code goes here
    values = process_file('c:/Users/admin/project/BGRYT/Python-WEB-Project/test_fol/Final_5min_RSI_ZEEL_from_2025-01-01_to_2025-11-19.csv')

    end_time = time.perf_counter()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.6f} seconds")