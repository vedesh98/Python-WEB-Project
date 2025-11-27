import os
import pandas as pd
import numpy as np

def analyze_combinations(csv_file, investment_per_trade=100000, risk_free_rate=0.05):
    df = pd.read_csv(csv_file, parse_dates=["entry_date", "exit_date"])
    # df["holding_days"] = (df["exit_date"] - df["entry_date"]).dt.days + 1

    summary = []

    # Group by RSI & SL%
    for (rsi, sl), group in df.groupby(["rsi", "percentage_move"]):
        group = group.copy()
        
        # Returns relative to capital per trade
        group["return"] = group["pnl"] / investment_per_trade  
        
        # Equity curve (sequential reinvestment)
        group["cum_pnl"] = group["pnl"].cumsum()
        group["equity_curve"] = investment_per_trade + group["cum_pnl"] - group["pnl"].iloc[0]  # shift back
        start_equity = investment_per_trade

        # Metrics
        total_trades = len(group)
        winning_trades = (group["pnl"] > 0).sum()
        losing_trades = (group["pnl"] <= 0).sum()
        win_ratio = winning_trades / total_trades if total_trades > 0 else 0

        # avg_holding = group["holding_days"].mean()
        # max_holding = group["holding_days"].max()
        # min_holding = group["holding_days"].min()

        # max_gain = group["pnl"].max()
        # min_gain = group["pnl"].min()

        # start_date = group["entry_date"].min()
        # end_date = group["exit_date"].max()
        # years = (end_date - start_date).days / 365
        # end_equity = group["equity_curve"].iloc[-1]
        # start_equity = group["equity_curve"].iloc[0]
        # cagr = (end_equity / start_equity) ** (1 / years) - 1 if years > 0 else 0
        # ratio = end_equity / start_equity if start_equity > 0 else 0
        # if years > 0 and ratio > 0:
        #     cagr = ratio ** (1 / years) - 1
        # else:
        #     cagr = 0

        # mean_return = group["return"].mean()
        # std_return = group["return"].std()
        # sharpe = ((mean_return - risk_free_rate/252) / std_return * np.sqrt(252)
        #           if std_return > 0 else np.nan)

        # rolling_max = group["equity_curve"].cummax()
        # drawdown = (group["equity_curve"] - rolling_max) / rolling_max
        # max_drawdown = drawdown.min()

        summary.append({
            "rsi": rsi,
            "sl_pct": sl,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_ratio": round(win_ratio, 4),
            # "avg_holding_days": round(avg_holding, 2),
            # "max_holding_days": max_holding,
            # "min_holding_days": min_holding,
            # "max_gain": round(max_gain, 2),
            # "min_gain": round(min_gain, 2),
            # "sharpe_ratio": round(sharpe, 4),
            # "max_drawdown": round(max_drawdown, 4),
            # "cagr": round(cagr, 4),
            # "start_equity": round(start_equity, 2),
            # "end_equity": round(end_equity, 2)
        })

    # Create DataFrame & sort by CAGR (best to worst)
    summary_df = pd.DataFrame(summary)
    summary_df = summary_df.sort_values(by="win_ratio", ascending=False).reset_index(drop=True)
    return summary_df

def analyze_group(group, investment_per_trade=100000, risk_free_rate=0.06):
    group = group.copy()


    # Proper equity curve (starting from 200k flat)
    group["cum_pnl"] = group["pnl"].cumsum()
    group["equity_curve"] = investment_per_trade + group["cum_pnl"] - group["pnl"].iloc[0]
    start_equity = investment_per_trade
    end_equity = start_equity + group["pnl"].sum()

    # Metrics
    total_trades = len(group)
    winning_trades = (group["pnl"] > 0).sum()
    losing_trades = (group["pnl"] <= 0).sum()
    win_ratio = winning_trades / total_trades if total_trades > 0 else 0

    # avg_holding = group["holding_days"].mean()
    # max_holding = group["holding_days"].max()
    # min_holding = group["holding_days"].min()

    max_gain = group["pnl"].max()
    min_gain = group["pnl"].min()

    # start_date = group["entry_date"].min()
    # end_date = group["exit_date"].max()
    # years = (end_date - start_date).days / 365
    # cagr = (end_equity / start_equity) ** (1 / years) - 1 if years > 0 else 0
    ratio = end_equity / start_equity if start_equity > 0 else 0
    # if years > 0 and ratio > 0:
    #     cagr = ratio ** (1 / years) - 1
    # else:
    #     cagr = 0

    # mean_return = group["return"].mean()
    # std_return = group["return"].std()
    # sharpe = ((mean_return - risk_free_rate/252) / std_return * np.sqrt(252)
    #           if std_return > 0 else np.nan)

    # rolling_max = group["equity_curve"].cummax()
    # drawdown = (group["equity_curve"] - rolling_max) / rolling_max
    # max_drawdown = drawdown.min()

    return {
        "rsi": group["rsi"].iloc[0],
        "sl_pct": group["percentage_move"].iloc[0],
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_ratio": round(win_ratio, 4) * 100,
        # "avg_holding_days": round(avg_holding, 2),
        # "max_holding_days": max_holding,
        # "min_holding_days": min_holding,
        # "max_gain": round(max_gain, 2),
        # "min_gain": round(min_gain, 2),
        # "sharpe_ratio": round(sharpe, 4),
        # "max_drawdown": round(max_drawdown, 4),
        # "cagr": round(cagr, 4),
        # "start_equity": round(start_equity, 2),
        # "end_equity": round(end_equity, 2),
        # "total_return_pct": round((end_equity - start_equity) / start_equity, 4)
    }

def analyze_all_trades(folder_path):
    all_results = []
    for file in os.listdir(folder_path):
        if file.endswith("Treads.csv"):
            symbol = file.replace("_Treads.csv", "")
            if symbol == 'NIFTY50':
                continue
            df = pd.read_csv(os.path.join(folder_path, file), parse_dates=["entry_time", "exit_time"])
            print(symbol)
            #Group RSI x SL%
            for (rsi, sl), group in df.groupby(["rsi", "percentage_move"]):
                metrics = analyze_group(group)
                metrics['symbol'] = symbol
                all_results.append(metrics)

    # Consolidate
    summary_df = pd.DataFrame(all_results)
    # summary_df = summary_df.sort_values(by="cagr", ascending=False).reset_index(drop=True)
    summary_df.to_csv("c:/Users/admin/project/BGRYT/Python-WEB-Project/nifty500_single_summary.csv", index=False)
    return summary_df

summary_df = analyze_all_trades("c:/Users/admin/project/BGRYT/Python-WEB-Project/treads")
print(summary_df.head(20))


# Example usage
# summary_df = analyze_combinations("/Users/umanggohil/Documents/BGYRT/dev-work/General/onservations/symbol_trades/CDSL_trades.csv", investment_per_trade=200000)
# print(summary_df.head(10))  # top 10 combos

