import pandas as pd
# import numpy as np
import requests
from datetime import datetime
import socket
import uuid
# import http.client
import time
import requests # type: ignore
# import mimetypes
import json
import talib
# import gdown
import http
import ssl
import os
# from concurrent.futures import ProcesPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor, as_completed
from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
import pyotp
from logzero import logger
from dotenv import load_dotenv
import multiprocessing
load_dotenv()


# Static values
user_type = "USER"
source_id = "WEB"   
api_key = os.environ["ANG_ONE_KEY"]  
client_code = os.environ["CLIENTCODE"]
password = os.environ["PASSWORD"]
window = 965

bot_token =  os.environ["BOT_TOKEN"]
test_mode = os.environ["TEST_MODE"].lower() == 'true'


# todays_date = datetime.today().strftime("%Y-%m-%d")
todays_date = (datetime.today() - pd.DateOffset(days=0)).strftime("%Y-%m-%d")
# window_date = (datetime.today() - pd.DateOffset(days=window)).strftime("%Y-%m-%d")
window_date = datetime(2025,1,1).strftime("%Y-%m-%d")
# '2025-01-01'  # Future date to include all data



local_ip = socket.gethostbyname(socket.gethostname())
smartApi = SmartConnect(api_key)

try:
    token = os.environ["TOTP_TOKEN"]
    totp = pyotp.TOTP(token).now()
except Exception as e:
    logger.error("Invalid Token: The provided token is not valid.")
    raise e


# Get Public IP
public_ip = requests.get('https://api.ipify.org').text

# Get MAC Address
mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0,8*6,8)][::-1])

# Change clientcode, password, totp
payload = '''{\n\"clientcode\":\"'''+str(client_code)+'''\"
         ,\n\"password\":\"'''+str(password)+'''\"\n
		,\n\"totp\":\"'''+str(totp)+'''\"\n
    ,\n\"state\":\"Active\"\n}'''

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    "X-UserType": user_type,
    "X-SourceID": source_id,
    "X-ClientLocalIP": local_ip,
    "X-ClientPublicIP": public_ip,
    "X-MACAddress": mac_address,
    'X-PrivateKey': api_key 
}


context = ssl._create_unverified_context()

conn = http.client.HTTPSConnection(
    "apiconnect.angelone.in", context=context
    )

conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)

res = conn.getresponse()
data = res.read()
data = data.decode("utf-8")



temp = json.loads(data)
jwtToken = temp["data"]["jwtToken"]
# print(jwtToken)


local_ip = socket.gethostbyname(socket.gethostname())
public_ip = requests.get('https://api.ipify.org').text
mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0,8*6,8)][::-1])
authToken = f'Bearer {jwtToken}'


headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    "X-UserType": user_type,
    "X-SourceID": source_id,
    "X-ClientLocalIP": local_ip,
    "X-ClientPublicIP": public_ip,
    "X-MACAddress": mac_address,
    'X-PrivateKey': api_key,
    'Authorization': authToken ,
}



# Download the file using gdown
output_file = 'c:/Users/admin/project/BGRYT/Python-WEB-Project/Nifty500-token.csv'
stock_symbols_df = pd.read_csv(output_file)
stock_symbols_df["token"] = stock_symbols_df["token"].fillna(891)
stock_symbols_df["token"] = stock_symbols_df["token"].astype(int)
# stocks_to_consider = 'Stocks.csv'

# stock_lists = pd.read_csv(stocks_to_consider)
# full_main_df = pd.merge(stock_lists[['rsi','symbol','win_ratio','priority']], stock_symbols_df[['Symbol','token']], left_on ='symbol' , right_on='Symbol', how='inner')


# # full_main_df.to_csv('Full_Main_df.csv', index=False)

main_df = stock_symbols_df.copy()

# full_main_df = pd.read_csv('Full_Main_df.csv')



# Step 2: Function to fetch daily candle data from API
def fetch_candle_data(symbol,interval='FIVE_MINUTE'):

    all_data = []
    start_date = window_date
    print(symbol, start_date)
    end_date = todays_date

    while start_date < end_date:
        time.sleep(0.4)  # To avoid hitting API rate limits
        chunk_end = (pd.to_datetime(start_date) + pd.DateOffset(days=100)).strftime("%Y-%m-%d")
        print(f"Fetching: {start_date}  →  {chunk_end}")
        
        payload = '''{\r\n     \"exchange\": \"NSE\",\r\n
          \"symboltoken\": \"'''+str(symbol)+'''\",\r\n     \"interval\": \"'''+str(interval)+'''\",\r\n
          \"fromdate\": \"'''+str(start_date)+''' 09:15\",\r\n     \"todate\": \"'''+str(chunk_end)+''' 16:30\"\r\n}
    '''

        conn = http.client.HTTPSConnection("apiconnect.angelone.in", context=context)
        conn.request("POST", "/rest/secure/angelbroking/historical/v1/getCandleData", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data = data.decode("utf-8")
        json_data = json.loads(data)
        json_data = json_data['data']
       
        
        if not json_data:
            print(f"No data returned for {start_date} to {chunk_end}.")
            raise json_data['message']
            break
        all_data.extend(json_data)
        

        start_date = (pd.to_datetime(chunk_end)  + pd.DateOffset(days=1)).strftime("%Y-%m-%d")

    # if all_data:
        # print(all_data)
    return all_data

    

# Prepare output DataFrame
error_data = []

final_df = pd.DataFrame()
print(main_df.columns.tolist())

# Step 5: Process each stock
#iterate only first 5 rows from 2nd row ingnore 1st

    # time.sleep(0.4)
def fetch_and_process(row):
    name = row['Symbol']
    token = row['token']
    print(f"Processing {name} with token {token}")
    try:   
        # Fetch daily data
        daily_json_data = fetch_candle_data(token)
        
        if daily_json_data == None:
            error_data.append({
               'Name': name,
               'Token': token,
               'reasone': 'Error while fetching data'
             })    
            return
        
        # logger.info(f"Processing {name} with token {token} and RSI {rsi}")
        
        df = pd.DataFrame(daily_json_data, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        
        # break

        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])

        # Sort data by date in ascending order
        df = df.sort_values('Date').reset_index(drop=True)

        df['RSI_14'] = talib.RSI(df['Close'], timeperiod=14)
        # keep 2 numbers after decimal  
        df['RSI_14'] = df['RSI_14'].round(2)
        df.set_index('Date', inplace=True)
        df['Token'] = token
        df['Symbol'] = name
        
        # final_df = pd.concat([final_df, df])
        
        # last_2_rsi_daily = df['RSI_14'].dropna().tail(2).values      
        last_dats = daily_json_data[-1][0].split('T')[0]
        
        df.dropna(subset=["Close", "High", "Low", "RSI_14"], inplace=True)
        #reset the index
        df = df.reset_index(drop=True)
        
        df.to_csv(f'c:/Users/admin/project/BGRYT/Python-WEB-Project/test_fol/Final_5min_RSI_{name}_from_{window_date}_to_{last_dats}.csv')
        

    except Exception as e:
        error_data.append({
            'Name': name,
            'Token': token,
            'reasone': str(e)
        })
        print(f"Error processing {name}: {e}")
        
        
        
        
if __name__ == "__main__":
    # for _, row in main_df.iterrows():
    #     fetch_and_process(row)
        
        
    cpu_cores = multiprocessing.cpu_count()
    max_workers = min(cpu_cores, len(main_df))
    print(f"Using {max_workers} CPU cores for processing.")
    
    with ProcessPoolExecutor(max_workers=1) as executor:
        futures = [executor.submit(fetch_and_process, row) for _, row in main_df.loc[:10].iterrows()]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Error in processing: {e}")
        
    if error_data:
        error_df = pd.DataFrame(error_data)
        error_df.to_csv('error_log.csv', index=False)
        print("Errors encountered during processing. See error_log.csv for details.")