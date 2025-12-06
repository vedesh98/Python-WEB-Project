




# Functional Programming Version of Your Script
# -------------------------------------------
# All functions are pure where possible, no shared state, no side‑effects except final file writes.

import os
import ssl
import http.client
import time
import json
import uuid
import socket
import pandas as pd
import talib
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# ----------------------------
# CONFIG LOADERS (PURE)
# ----------------------------
def load_env():
    return {
        "api_key": os.environ["ANG_ONE_KEY"],
        "client_code": os.environ["CLIENTCODE"],
        "password": os.environ["PASSWORD"],
        "totp_token": os.environ["TOTP_TOKEN"],
        "bot_token": os.environ.get("BOT_TOKEN", ""),
        "test_mode": os.environ.get("TEST_MODE", "false").lower() == "true",
    }

# ----------------------------
# AUTH HELPERS (PURE)
# ----------------------------
def get_system_headers():
    local_ip = socket.gethostbyname(socket.gethostname())
    public_ip = requests.get("https://api.ipify.org").text
    mac_address = ":".join([
        f"{(uuid.getnode() >> ele) & 0xff:02x}" for ele in range(0, 48, 8)
    ][::-1])
    return local_ip, public_ip, mac_address


def build_auth_payload(client_code, password, totp):
    return json.dumps({
        "clientcode": client_code,
        "password": password,
        "totp": totp,
        "state": "Active",
    })


def api_post(url, path, payload, headers):
    context = ssl._create_unverified_context()
    conn = http.client.HTTPSConnection(url, context=context)
    conn.request("POST", path, payload, headers)
    res = conn.getresponse()
    return res.read().decode("utf-8")


# ----------------------------
# LOGIN PROCESS (STATEFUL but encapsulated)
# ----------------------------
def authenticate(env):
    import pyotp

    totp = pyotp.TOTP(env["totp_token"]).now()
    auth_payload = build_auth_payload(env["client_code"], env["password"], totp)

    local_ip, public_ip, mac = get_system_headers()

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": local_ip,
        "X-ClientPublicIP": public_ip,
        "X-MACAddress": mac,
        "X-PrivateKey": env["api_key"],
    }

    raw = api_post(
        "apiconnect.angelone.in",
        "/rest/auth/angelbroking/user/v1/loginByPassword",
        auth_payload,
        headers,
    )
    jwt = json.loads(raw)["data"]["jwtToken"]

    # Return final headers
    return jwt


# ----------------------------
# CANDLE FETCHER (PURE)
# ----------------------------

def build_history_payload(token, start, end, interval):
    return json.dumps({
        "exchange": "NSE",
        "symboltoken": str(token),
        "interval": interval,
        "fromdate": f"{start} 09:15",
        "todate": f"{end} 16:30",
    })


def fetch_candle_range(token, start, end, interval, headers):
    payload = json.dumps({
        "exchange": "NSE",
        "symboltoken": str(token),
        "interval": interval,
        "fromdate": f"{start} 09:15",
        "todate": f"{end} 16:30",
    })
    
    raw = api_post(
        "apiconnect.angelone.in",
        "/rest/secure/angelbroking/historical/v1/getCandleData",
        payload,
        headers,
    )
    return json.loads(raw).get("data", [])


def fetch_all_candles(token, start_date, end_date, interval, headers):
    all_rows = []
    start = pd.to_datetime(start_date)
    end   = pd.to_datetime(end_date)

    while start < end:
        chunk_end = start + pd.DateOffset(days=100)
        chunk_end_fmt = min(chunk_end, end).strftime("%Y-%m-%d")
        start_fmt = start.strftime("%Y-%m-%d")

        rows = fetch_candle_range(token, start_fmt, chunk_end_fmt, interval, headers)
        time.sleep(0.4)

        if rows:
            all_rows.extend(rows)

        start = chunk_end + pd.DateOffset(days=1)

    return all_rows


# ----------------------------
# PURE TRANSFORMERS
# ----------------------------

def json_to_df(rows):
    df = pd.DataFrame(rows, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def add_indicators(df):
    df["RSI_14"] = talib.RSI(df["Close"], timeperiod=14).round(2)
    df = df.dropna(subset=["RSI_14", "Open", "High", "Low", "Close"])
    return df


# ----------------------------
# MAIN PROCESSOR (PURE)
# ----------------------------

def process_stock(symbol, token, headers, start_date, end_date):
    rows = fetch_all_candles(token, start_date, end_date, "FIVE_MINUTE", headers)
    if not rows:
        raise Exception(f"No data returned for token {token}")

    df = json_to_df(rows)
    df = add_indicators(df)
    df["Symbol"] = symbol
    df["Token"] = token
    df.set_index("Date", inplace=True)

    return df


# ----------------------------
# DRIVER (MUTATION ONLY AT END)
# ----------------------------

def run():
    env = load_env()
    jwt = authenticate(env)

    local_ip, public_ip, mac = get_system_headers()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": local_ip,
        "X-ClientPublicIP": public_ip,
        "X-MACAddress": mac,
        "X-PrivateKey": env["api_key"],
        "Authorization": f"Bearer {jwt}",
    }

    df = pd.read_csv("c:/Users/admin/PO1/Python-WEB-Project/Nifty500-token.csv")
    df["token"] = df["token"].fillna(891).astype(int)

    start_date = "2025-01-01"
    end_date = datetime.today().strftime("%Y-%m-%d")

    results = []

    for _, row in df.iloc[:508].iterrows():
        try:
            stock_df = process_stock(row["Symbol"], row["token"], headers, start_date, end_date)
            out = f"c:/Users/admin/PO1/Python-WEB-Project/5min test/{row['Symbol']}_Candle.csv"
            stock_df.to_csv(out)
            results.append((row["Symbol"], "OK"))
        except Exception as e:
            results.append((row["Symbol"], str(e)))

    return results


if __name__ == "__main__":
    
    start_time = time.perf_counter()
    print(len(run()))
    end_time = time.perf_counter()
    execution_time = end_time - start_time

    print(f"Execution time: {execution_time:.6f} seconds")