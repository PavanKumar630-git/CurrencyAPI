from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
import cloudscraper
import json

app = FastAPI(title="Thomas Cook RateCards Proxy API")

from datetime import datetime, timedelta, timezone

def get_current_time_in_utc_and_ist():
    """
    Returns the current UTC and IST time in human-readable format,
    along with the Unix timestamps (seconds and milliseconds).
    """
    # Current UTC time
    dt_utc = datetime.now(timezone.utc)

    # IST = UTC + 5:30
    ist_offset = timedelta(hours=5, minutes=30)
    dt_ist = dt_utc + ist_offset

    # Convert to Unix timestamps
    unix_sec = int(dt_utc.timestamp())
    unix_ms = int(dt_utc.timestamp() * 1000)

    return {
        "utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC",
        "ist": dt_ist.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " IST",
        "timestamp_seconds": unix_sec,
        "timestamp_milliseconds": unix_ms
    }

def get_thomascook_cookies():
    """
    Fetches cookies 'c2Vzc2lvbklk' and 'requestId' from Thomas Cook Forex Rate Card page.
    Returns a dict like:
        {
            "c2Vzc2lvbklk": "...",
            "requestId": "..."
        }
    """
    url = "https://www.thomascook.in/foreign-exchange/forex-rate-card"
    target_cookies = ["c2Vzc2lvbklk", "requestId"]

    with requests.Session() as s:
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        resp = s.get(url, timeout=20)
        resp.raise_for_status()

        all_cookies = s.cookies.get_dict()

        # Return only the required cookies
        result = {name: all_cookies.get(name) for name in target_cookies}
        return result

@app.get("/thomascook")
def get_ratecards():
    cookies = get_thomascook_cookies()
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.thomascook.in/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Origin': '*',
        'requestId': cookies.get('requestId',''),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'application/json; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8',
        'sessionId': cookies.get('c2Vzc2lvbklk',''),
    }
    result = get_current_time_in_utc_and_ist()
    params = {
        '_': result["timestamp_milliseconds"]
    }

    try:
        resp = requests.get(
            "https://services.thomascook.in/tcRevampForexRS/generic/rateCards/2",
            headers=headers,
            params=params,
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()

        # Transform response
        transformed = [
            {
                "platform": "thomascook",
                "currencycode": item.get("currencyCode", ""),
                "currencyname": item.get("currencyName", ""),
                "moduletype": item.get("moduleType", ""),
                "productname": item.get("productName", ""),
                "roe": item.get("roe", "")
            }
            for item in data.get("listModuleProductRoeMappingBean", [])
        ]

        return JSONResponse(content=transformed, status_code=200)

    except requests.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


def map_rate_card_to_bookmyforex(data):
    mapped_data = []
    
    for item in data.get("result", []):
        currency_code = item.get("currency_code")
        currency_name = item.get("currency_description")
        
        # Buy entry using 'bcn'
        if item.get("bcn"):
            mapped_data.append({
                "platform": "bookmyforex",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "buy",
                "productname": "",
                "roe": float(item["bcn"])
            })
        
        # Sell entry using 'scn'
        if item.get("scn"):
            mapped_data.append({
                "platform": "bookmyforex",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "sell",
                "productname": "",
                "roe": float(item["scn"])
            })
    
    return mapped_data

BOOKMYFOREX_URL = "https://www.bookmyforex.com/api/secure/v1/get-full-rate-card"

@app.get("/bookmyforex/ratecard")
def get_bookmyforex_ratecard(city_code: str = "DEL"):
    """
    Fetch full rate card from BookMyForex for the given city_code.
    Headers and cookies are defined inside the function.
    """
    cookies = {
        'JSESSIONID': '150DsdfsfdsfdsfC56D72CAFE0D15FD420F87BC92EF',
        '_sec_token_csrf': 'b13csdfdsf68f7-99ac-4d22-9f6d-38e7604b91a7',
        # add other necessary cookies here
    }

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'content-type': 'application/json',
        'referer': 'https://www.bookmyforex.com/fullratecard/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    try:
        params = {"city_code": city_code}
        response = requests.get(BOOKMYFOREX_URL, params=params, headers=headers)
        response.raise_for_status()
        final_data = map_rate_card_to_bookmyforex(response.json())
        return JSONResponse(content=final_data)
    except requests.RequestException as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    
def map_rate_card_to_oreichange(data):
    mapped_data = []
    
    for item in data:
        currency_code = item.get("ccode")
        currency_name = item.get("cname")
        
        # Buy entry using 'bcn'
        if item.get("buy"):
            mapped_data.append({
                "platform": "orientexchange",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "Customer Sell Currency",
                "productname": "Customer Sell Currency",
                "roe": item.get('buy')
            })
        
        # Sell entry using 'scn'
        if item.get("tcsell"):
            mapped_data.append({
                "platform": "orientexchange",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "Customer Buy - Card",
                "productname": "Card",
                "roe": item.get('tcsell',0)
            })
        # Sell entry using 'scn'
        if item.get("cnsell"):
            mapped_data.append({
                "platform": "orientexchange",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "Customer Buy - Currency",
                "productname": "Currency",
                "roe": item.get('cnsell',0)
            })

        # Sell entry using 'scn'
        if item.get("adtwo"):
            mapped_data.append({
                "platform": "orientexchange",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "Outward Remittance-Educational/Medical",
                "productname": "Educational/Medical",
                "roe": item.get('adtwo',0)
            })

        # Sell entry using 'scn'
        if item.get("adone"):
            mapped_data.append({
                "platform": "orientexchange",
                "currencycode": currency_code,
                "currencyname": currency_name,
                "moduletype": "Outward Remittance-Maintenance /Gift",
                "productname": "Maintenance /Gift",
                "roe": item.get('adone',0)
            })
    
    
    return mapped_data

@app.get("/orientexchange/live-rates")
def get_orientexchange_live_rates():
    """
    Fetch live exchange rates from Orient Exchange using cloudscraper.
    Returns a JSON response with currency rates.
    """
    try:
        scraper = cloudscraper.create_scraper()
        data = {'selLoc': '5', 'requestType': 'getLiveRates'}
        resp = scraper.post('https://www.orientexchange.in/live_exchange_rates', data=data)
        
        if resp.status_code != 200:
            return JSONResponse(content={"error": f"Failed to fetch rates, status code {resp.status_code}"}, status_code=resp.status_code)
        jsondata  = json.loads(resp.text)
        final_data = map_rate_card_to_oreichange(jsondata)
        return final_data
    except:
        return JSONResponse(content={"error": f"Failed to fetch rates, status code {resp.status_code}"}, status_code=resp.status_code)
