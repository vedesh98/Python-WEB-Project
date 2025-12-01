import pandas as pd
import requests
from datetime import datetime
import socket
import uuid
import time
import json
import talib
import http
import ssl
import os

from SmartApi import SmartConnect 
import pyotp
from logzero import logger


from dotenv import load_dotenv
load_dotenv()


# Static values
user_type = "USER"
source_id = "WEB"  
api_key = os.environ["ANG_ONE_KEY"]  
client_code = os.environ["CLIENTCODE"]
password = os.environ["PASSWORD"]

bot_token = os.environ["BOT_TOKEN"]
test_mode = os.environ["TEST_MODE"].lower() == 'true'



TEST_ID = "529251493"
if test_mode:
    CHAT_ID = TEST_ID
else:
    CHAT_ID = "-1003139839259"

# Prepare output DataFrame
error_data = []
priority_data = []
priority_data_01 = []

window = 365

todays_date = (datetime.today() - pd.DateOffset(days=0)).strftime("%Y-%m-%d")
window_date = (datetime.today() - pd.DateOffset(days=window)).strftime("%Y-%m-%d")

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

current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, "Main_df.csv")

main_df = pd.read_csv(file_path)


# Step 2: Function to fetch daily candle data from API
def fetch_candle_data(symbol,interval='ONE_DAY',error_reprocess=False):
  
    payload = '''{\r\n     \"exchange\": \"NSE\",\r\n
          \"symboltoken\": \"'''+str(symbol)+'''\",\r\n     \"interval\": \"'''+str(interval)+'''\",\r\n
          \"fromdate\": \"'''+str(window_date)+''' 16:30\",\r\n     \"todate\": \"'''+str(todays_date)+''' 16:30\"\r\n}
    '''    
    conn = http.client.HTTPSConnection("apiconnect.angelone.in", context=context)
    conn.request("POST", "/rest/secure/angelbroking/historical/v1/getCandleData", payload, headers)
    res = conn.getresponse()
    data = res.read()
    data = data.decode("utf-8")
    json_data = json.loads(data)    
    json_data = json_data['data']
    
    if not json_data:
      if error_reprocess == False:
        time.sleep(0.4)
        return fetch_candle_data(symbol, interval, True)
      raise json_data['message']
    return json_data
  

# Fuction to identify RSI Breakout
def rsi_trend(rsi_values, setup_rsi):
    if rsi_values[-1] >= setup_rsi and  rsi_values[-2] < setup_rsi:
      return True
    


# Fecth candel data and Calculate RSI for each stock 
def process_stock(row,processing_count=1):
    # error_data = []
    time.sleep(0.4)

    priority = row['priority']
    name = row['Symbol']
    token = row['token']
    rsi = row['rsi']
    win_ratio = row['win_ratio']
    try:

        if rsi == None:
            error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': 'RSI Not Maintained in file'
             }) 
            return
   
   
        # Fetch daily data
        daily_json_data = fetch_candle_data(token)
        if daily_json_data == None:
            error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': 'Error while fetching data'
             })    
            return
         
        df = pd.DataFrame(daily_json_data, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
        
        # break

        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])

        # Sort data by date in ascending order
        df = df.sort_values('Date').reset_index(drop=True)

        df['RSI_14'] = talib.RSI(df['Close'], timeperiod=14)
        df.set_index('Date', inplace=True)
                
        last_2_rsi_daily = df['RSI_14'].dropna().tail(2).values


        if len(last_2_rsi_daily) < 2:
            error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': 'Not enough RSI data'
             })
             
            return
        
        daily_rsi = last_2_rsi_daily[-1]

        last_dats = daily_json_data[-1][0].split('T')[0]
        
        if last_dats != todays_date:
            error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': f'Date from API {last_dats}, processing date {todays_date}'
             })
             
            return


        if priority == 2:
            # if rsi_trend(last_2_rsi_daily, rsi):
            # Check RSI breakout condition
            if last_2_rsi_daily[-1] >= rsi and  last_2_rsi_daily[-2] < rsi:
                priority_data.append({                    
                    'Name': name,
                    'Token': token,
                    'Setup_RSI': rsi,
                    'Daily_RSI': daily_rsi,
                    'yesterday_RSI': last_2_rsi_daily[-2],
                    'win_ratio': win_ratio,

                })
                # if processing_count > 1:
                #     priority_data_01.append({                    
                #         'Name': name,       
                #         'Token': token,
                #         'Setup_RSI': rsi,
                #         'Daily_RSI': daily_rsi,
                #         'yesterday_RSI': last_2_rsi_daily[-2],  
                #         'win_ratio': win_ratio,
                #     })

    except Exception as e:
        error_data.append({
            'Name': name,
            'Token': token,
            'Setup_RSI': rsi,
            'reasone': str(e)
        })
        # print(f"Error processing {name}: {e}")
        


# Formate stocks into message to send via Telegram/whatsapp
def format_whatsapp_report(data ,name):
    
    lines = [f"📊 <b>{name}</b>"]
    
    if len(data) == 0:
        lines.append( "\n🔹 <b>No Stocks</b>" )
    else:
        for index,item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1} {item['Name']}</b>"
                f"\n   <b>Todays RSI :</b> {item['Daily_RSI']:.2f}"
                f"\n   <b>Yesterdays RSI :</b> {item['yesterday_RSI']:.2f}"
                f"\n   <b>Standard RSI :</b> {item['Setup_RSI']:.2f}"
            )      
           
    return "\n".join(lines) 

# Formate error stocks into message to send via Telegram/whatsapp
def format_whatsapp_error(data ,name):
    
    lines = [f"📊 <b>{name}</b>"]
    
    if len(data) == 0:
        lines.append( "\n🔹 <b>No Stocks</b>" )
    else:
        for index,item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1} {item['Name']}</b>"
                f"\n   <b>Token: </b> {item['Token']}"
                f"\n   <b>Standard RSI: </b> #{item['Setup_RSI']:.2f}"
                f"\n   <b>Reasone: </b> {item['reasone']}"
            )      
           
    return "\n".join(lines)


# Step 5: Process each stock
for _, row in main_df[main_df['priority'] == 2].iterrows():
    process_stock(row)
    

# Telegram Message trigger logic
if len(priority_data) > 0:
    msg = f"📊 <b>Live Stock: {todays_date}</b>"
    requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                params={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

    msg_p1 = format_whatsapp_report(priority_data,'Priority Stocks')
    requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                params={"chat_id": CHAT_ID, "text": msg_p1, "parse_mode": "HTML"})
    

if len(error_data) > 0:
    error_msg = format_whatsapp_error(error_data,'Error Stocks')
    requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                params={"chat_id": TEST_ID, "text": error_msg, "parse_mode": "HTML"})
    


