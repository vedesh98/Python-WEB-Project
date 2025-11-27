import pandas as pd
import requests
from datetime import datetime
import socket
import uuid
import time
import requests # type: ignore
import json
import talib
import http
import ssl
import os

from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
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
window = 965

bot_token =  os.environ["BOT_TOKEN"]
test_mode = os.environ["TEST_MODE"].lower() == 'true'


todays_date = (datetime.today() - pd.DateOffset(days=0)).strftime("%Y-%m-%d")
window_date = (datetime.today() - pd.DateOffset(days=window)).strftime("%Y-%m-%d")

local_ip = socket.gethostbyname(socket.gethostname())
smartApi = SmartConnect(api_key)

try:
    # token = os.getenv("TOTP_TOKEN")
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
def fetch_candle_data(symbol,interval='ONE_DAY'):
  
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
      raise json_data['message']
    
    return json_data

# Step 4: Function to calculate RSI trends (increase or decrease)
def rsi_trend1(rsi_values, setup_rsi):
    if rsi_values[-1] >= 60 and  rsi_values[-2] < 60:
      return "60 CROSSOVER"

    if rsi_values[-1] >= setup_rsi and  rsi_values[-2] < setup_rsi:
      return setup_rsi + 1

    if rsi_values[-1] < setup_rsi and rsi_values[-2] >= setup_rsi:
      return setup_rsi - 1

    if rsi_values[-1] > rsi_values[-2]:
        return 'UP'
    else:
        return 'DOWN'
    

# Fuction to identify RSI Breakout
def rsi_trend(rsi_values, setup_rsi):
    if rsi_values[-1] >= setup_rsi and  rsi_values[-2] < setup_rsi:
      return True
    

# Fuction to identify stocks before RSI Breakout 
def rsi_trend_P1(rsi_values, setup_rsi):    
    if rsi_values[-1] >= ( setup_rsi - 5 ) and  rsi_values[-1] < ( setup_rsi + 5):
      return True
     
def fetch_candle_week_month_data(symbol,range='W',daily_json_data=None):
    
    if daily_json_data is None:
      daily_json_data = fetch_candle_data(symbol)
      
    df = pd.DataFrame(daily_json_data, columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    # Convert 'Date' column to datetime
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)

    # Make Date the DatetimeIndex required by resample
    df.set_index('Date', inplace=True)
    
    # # Sort data by date in ascending order
    # df = df.sort_values('Date').reset_index(drop=True)

    range_data = df.resample(range).agg({
    # 'Date' : 'last',
    'Open': 'first',
    'High': 'max',
    'Low': 'min',
    'Close': 'last',
    'Volume': 'sum'
      }).dropna()
    
    

    range_data['RSI_14'] = talib.RSI(range_data['Close'], timeperiod=14)
    return range_data
    

    # Prepare output DataFrame
output_data = []
error_data = []
priority_data = []
priority_watch_data = []
priority0_data = []
rsi_40_cross_data = []

# print(main_df.columns.tolist())

# Step 5: Process each stock
for _, row in main_df.iterrows():

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
            continue
   
   
        # Fetch daily data
        daily_json_data = fetch_candle_data(token)
        if daily_json_data == None:
            error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': 'Error while fetching data'
             })    
            continue
        # print(daily_json_data)

        monthly_data = fetch_candle_week_month_data(token,'ME',daily_json_data)   
        
        # print(monthly_data)
        # logger.info(f"Processing {name} with token {token} and RSI {rsi}")
        last_2_rsi_monthly = monthly_data['RSI_14'].dropna().tail(2).values
        
        if len(last_2_rsi_monthly) < 2:
             error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': 'Not enough Monthly RSI data'
             })
             continue
         
        # if rsi_trend1(last_2_rsi_monthly,40) == "39":
        if last_2_rsi_monthly[-2] <= 40 or last_2_rsi_monthly[-1] <= 40:
            rsi_40_cross_data.append({
                'Name': name,
                'Token': token,
                'Monthly_RSI': last_2_rsi_monthly[-1],
                'last_Month_RSI': last_2_rsi_monthly[-2],
                'Priority': priority,
            })


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
             continue
        daily_rsi = last_2_rsi_daily[-1]

        last_dats = daily_json_data[-1][0].split('T')[0]
        
        if last_dats != todays_date:
             error_data.append({
               'Name': name,
               'Token': token,
               'Setup_RSI': rsi,
               'reasone': f'Date from API {last_dats}, processing date {todays_date}'
             })
             continue

        if priority == 2:
            if rsi_trend(last_2_rsi_daily, rsi):
                priority_data.append({
                    'Name': name,
                    'Token': token,
                    'Setup_RSI': rsi,
                    'Daily_RSI': daily_rsi,
                    'yesterday_RSI': last_2_rsi_daily[-2],
                    'win_ratio': win_ratio,

                })
                continue

            if rsi_trend_P1(last_2_rsi_daily, rsi):
                priority_watch_data.append({
                    'Name': name,
                    'Token': token,
                    'Setup_RSI': rsi,
                    'Daily_RSI': daily_rsi,
                    'yesterday_RSI': last_2_rsi_daily[-2],
                    'win_ratio': win_ratio,

                })
                
        elif priority == 1 and rsi_trend(last_2_rsi_daily, rsi):
            output_data.append({
                'Name': name,
                'Token': token,
                'Setup_RSI': rsi,
                'Daily_RSI': daily_rsi,
                'yesterday_RSI': last_2_rsi_daily[-2],
                'win_ratio': win_ratio,
            })

        elif priority == 0 and rsi_trend(last_2_rsi_daily, rsi):
            priority0_data.append({
                'Name': name,
                'Token': token,
                'Setup_RSI': rsi,
                'Daily_RSI': daily_rsi,
                'yesterday_RSI': last_2_rsi_daily[-2],
                'win_ratio': win_ratio,
            })
           
                      

        

    except Exception as e:
        error_data.append({
            'Name': name,
            'Token': token,
            'Setup_RSI': rsi,
            'reasone': str(e)
        })
        print(f"Error processing {name}: {e}")
        
        
        

BOT_TOKEN = bot_token

TEST_ID = "529251493"

if test_mode:
    CHAT_ID = TEST_ID
else:
    CHAT_ID = "-1003139839259"
    
def format_whatsapp_report(data ,name):
    
    
    if len(data) == 0:
        lines = [f"📊 <b>{name} : 0 Stocks </b>"]
    else:
        lines = [f"📊 <b>{name}</b>"]
        for index,item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1} {item['Name']}</b>"
                f"\n   <b>Todays RSI: </b> {item['Daily_RSI']:.2f}"
                f"\n   <b>Yesterdays RSI: </b> {item['yesterday_RSI']:.2f}"
                f"\n   <b>Standard RSI: </b> {item['Setup_RSI']:.2f}"
                # f"\n   High Priority: {'✅' if item['High Priority'] else '❌'}"
            )      
           
    return "\n".join(lines) 

def format_whatsapp_error(data ,name):
    
    lines = [f"📊 <b>{name}</b>"]
    
    if len(data) == 0:
        lines.append( "\n🔹 <b>No Stocks</b>" )
    else:
        for index,item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1} {item['Name']}</b>"
                f"\n   <b>Token: </b> {item['Token']}"
                f"\n   <b>Standard RSI: </b> {item['Setup_RSI']:.2f}"
                f"\n   <b>Reasone: </b> {item['reasone']}"
                # f"\n   High Priority: {'✅' if item['High Priority'] else '❌'}"
            )      
           
    return "\n".join(lines)

def format_whatsapp_40_report(data ,name):
    
    
    if len(data) == 0:
        lines = [f"📊 <b>{name} : 0 Stocks </b>"]
    else:
        lines = [f"📊 <b>{name}</b>"]
        for index,item in enumerate(data):
            lines.append(
                f"\n🔹 <b>{index+1} {item['Name']}</b>"
                f"\n   <b>Current Month RSI: </b>{item['Monthly_RSI']:.2f}"
                f"\n   <b>Last Month RSI: </b>{item['last_Month_RSI']:.2f}"
                f"\n   <b>Priority: </b>{item['Priority']}"
            )      
           
    return "\n".join(lines) 

# Telegram Message trigger logic
msg = f"📊 <b>Daily Report: {todays_date}</b>"
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
             params={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"})

msg_p1 = format_whatsapp_report(priority_data,'Priority Stocks')
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
             params={"chat_id": CHAT_ID, "text": msg_p1, "parse_mode": "HTML"})


msg_p2 = format_whatsapp_report(priority_watch_data,'Priority Stocks to be tracked')
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
             params={"chat_id": CHAT_ID, "text": msg_p2, "parse_mode": "HTML"})

msg_t = format_whatsapp_report(output_data ,'Treading Stocks')
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
             params={"chat_id": CHAT_ID, "text": msg_t, "parse_mode": "HTML"})

msg_p0 = format_whatsapp_report(priority0_data,'Least Priority Stocks')
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg_p0, "parse_mode": "HTML"})



if len(error_data) > 0:
    error_msg = format_whatsapp_error(error_data,'Error Stocks')
    error_test = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                params={"chat_id": TEST_ID, "text": error_msg, "parse_mode": "HTML"})
    # print(error_test)
    
    
    
# if len(rsi_40_cross_data) > 0:
msg_40 = format_whatsapp_40_report(rsi_40_cross_data,'RSI 40 Crossover Stocks')
requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            params={"chat_id": TEST_ID, "text": msg_40, "parse_mode": "HTML"})

# print(error_msg)