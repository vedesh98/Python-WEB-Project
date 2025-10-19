import pandas as pd
import numpy as np
import requests
from datetime import datetime
import socket
import uuid
import http.client
import time
import requests # type: ignore
import mimetypes
import json
import talib
import gdown
import http
import ssl
from SmartApi import SmartConnect #or from SmartApi.smartConnect import SmartConnect
import pyotp
from logzero import logger

# Static values
user_type = "USER"
source_id = "WEB"
api_key = 'Qig2QzKR' 
window = 365

todays_date = datetime.today().strftime("%Y-%m-%d")
window_date = (datetime.today() - pd.DateOffset(days=window)).strftime("%Y-%m-%d")



local_ip = socket.gethostbyname(socket.gethostname())
smartApi = SmartConnect(api_key)

try:
    token = "QYO6BHBHL2LLY42CDR7CVIN5SU"
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
payload = '''{\n\"clientcode\":\"BGBG1144\"
            ,\n\"password\":\"2098\"\n
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
    'X-PrivateKey': api_key #'QNeuDKb5'
}


context = ssl._create_unverified_context()

conn = http.client.HTTPSConnection(
    "apiconnect.angelone.in", context=context
    )

conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)

res = conn.getresponse()
data = res.read()
data = data.decode("utf-8")
print(data)

temp = json.loads(data)
jwtToken = temp["data"]["jwtToken"]
print(jwtToken)

# user_type = "USER"
# source_id = "WEB"
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
    'X-PrivateKey': api_key, #'QNeuDKb5',
    'Authorization': authToken ,
}

# shareable_link = 'https://drive.google.com/file/d/1PdYMxjWQ4tBJp4Mmp1LjLOR2H2vkZ6on/view?usp=sharing'

# Extract the file ID
# file_id = shareable_link.split('/d/')[1].split('/view')[0]

# Construct the download URL
# download_url = f'https://drive.google.com/uc?id={file_id}'


# # Download the file using gdown
# output_file = 'Nifty500-token.csv'

# stock_symbols_df = pd.read_csv(output_file)
# stock_symbols_df["token"] = stock_symbols_df["token"].fillna(891)
# stock_symbols_df["token"] = stock_symbols_df["token"].astype(int)
# stocks_to_consider = 'PO1_Stocks.csv'

# stock_lists = pd.read_csv(stocks_to_consider)
# main_df = pd.merge(stock_lists[['rsi','symbol','win_ratio','priority']], stock_symbols_df[['Symbol','token']], left_on ='symbol' , right_on='Symbol', how='inner')

# main_df.to_csv('Main_df.csv', index=False)

main_df = pd.read_csv('Main_df.csv')