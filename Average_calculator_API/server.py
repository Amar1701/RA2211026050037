from fastapi import FastAPI, HTTPException
import httpx
import time
from collections import deque

app = FastAPI()

# API Configuration
THIRD_PARTY_APIS = {
    "p": "http://20.244.56.144/test/primes",
    "f": "http://20.244.56.144/test/fibo",
    "e": "http://20.244.56.144/test/even",
    "r": "http://20.244.56.144/test/rand"
}

# Store Token (Initially Empty)
ACCESS_TOKEN = None
TOKEN_EXPIRY = 0
WINDOW_SIZE = 10
number_window = deque(maxlen=WINDOW_SIZE)

async def get_access_token():
    """Fetches a new access token if expired."""
    global ACCESS_TOKEN, TOKEN_EXPIRY
    if time.time() < TOKEN_EXPIRY:
        return ACCESS_TOKEN

    token_url = "http://20.244.56.144/test/token"
    payload = {
        "clientID": "b5853394-fbab-496e-82ef-7fc820ced72d",
        "clientSecret": "GlSYNwUHwntVJOBy"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, json=payload)
            response.raise_for_status()
            data = response.json()
            ACCESS_TOKEN = data["access_token"]
            TOKEN_EXPIRY = time.time() + data["expires_in"] - 10  # Buffer of 10 sec
            return ACCESS_TOKEN
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=500, detail="Failed to fetch access token")

@app.get("/numbers/{numberid}")
async def get_numbers(numberid: str):
    if numberid not in THIRD_PARTY_APIS:
        raise HTTPException(status_code=400, detail="Invalid number ID")
    
    url = THIRD_PARTY_APIS[numberid]
    token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get(url, headers=headers)
        response_time = (time.time() - start_time) * 1000

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Error fetching numbers from external API")

        data = response.json()
        new_numbers = list(set(data.get("numbers", [])))

        prev_state = list(number_window)
        for num in new_numbers:
            if num not in number_window:
                number_window.append(num)

        curr_state = list(number_window)
        avg_value = round(sum(curr_state) / len(curr_state), 2) if curr_state else 0

        return {
            "windowPrevState": prev_state,
            "windowCurrState": curr_state,
            "numbers": new_numbers,
            "avg": avg_value,
            "response_time_ms": round(response_time, 2)
        }

    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="API request failed or timed out")
