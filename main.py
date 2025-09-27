from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests

app = FastAPI(title="Thomas Cook RateCards Proxy API")

@app.get("/thomascook")
def get_ratecards():
    headers = {
        'sec-ch-ua-platform': '"Windows"',
        'Referer': 'https://www.thomascook.in/',
        'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        'sec-ch-ua-mobile': '?0',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Access-Control-Allow-Origin': '*',
        'requestId': 'zG9X6Nb4q3',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Accept': 'application/json; charset=utf-8',
        'Content-Type': 'application/json; charset=utf-8',
        'sessionId': 'FX4A3VfSzn581897330',
    }

    params = {
        '_': '1758961760117',
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
    
# import time
# from selenium.webdriver.common.by import By
# import undetected_chromedriver as uc

# @app.get("/orientexchange/live-rates")
# def get_orientexchange_live_rates():
#     """
#     Fetch live exchange rates from Orient Exchange dynamically using Selenium.
#     Returns a JSON response with the live rates.
#     """
#     try:
#         # Configure Chrome options
#         options = uc.ChromeOptions()
#         options.headless = True  # run in headless mode
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-gpu")
#         options.add_argument("--disable-dev-shm-usage")
        
#         # Launch browser
#         driver = uc.Chrome(options=options)
#         driver.get("https://www.orientexchange.in/")
#         time.sleep(5)  # wait for page and JS to load

#         # Select the location dropdown (if necessary)
#         # Example: select Delhi (value=5)
#         sel = driver.find_element(By.ID, "selLoc")
#         for option in sel.find_elements(By.TAG_NAME, "option"):
#             if option.text.strip() == "Delhi":
#                 option.click()
#                 time.sleep(2)

#         # Click "Get Live Rates" button
#         button = driver.find_element(By.ID, "getLiveRates")  # replace with actual button ID
#         button.click()
#         time.sleep(5)  # wait for rates to load

#         # Extract rates table
#         table = driver.find_element(By.ID, "liveRatesTable")  # replace with actual table ID
#         rows = table.find_elements(By.TAG_NAME, "tr")

#         result = []
#         for row in rows[1:]:  # skip header
#             cols = row.find_elements(By.TAG_NAME, "td")
#             if len(cols) >= 5:
#                 result.append({
#                     "currency": cols[0].text.strip(),
#                     "buy_rate": cols[1].text.strip(),
#                     "sell_rate": cols[2].text.strip(),
#                     "remit_rate": cols[3].text.strip(),
#                     "notes": cols[4].text.strip(),
#                 })

#         driver.quit()
#         return JSONResponse(content={"platform": "orientexchange", "rates": result})

#     except Exception as e:
#         return JSONResponse(content={"error": str(e)}, status_code=500)
