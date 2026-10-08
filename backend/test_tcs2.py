import httpx

def test():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    resp = httpx.get(url, timeout=30.0)
    data = resp.json()
    
    for r in data:
        symbol = r.get("symbol", "")
        exch = r.get("exch_seg", "")
        std_symbol = symbol.replace("-EQ", "") if exch == "NSE" else symbol
        if exch == "NSE" and std_symbol == "TCS":
            print(f"Collision: {r}")

if __name__ == "__main__":
    test()
