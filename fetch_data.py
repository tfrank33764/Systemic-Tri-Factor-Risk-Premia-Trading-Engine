from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
import requests
import json
import time

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok = True)
API_KEY  = os.environ["EODHD_API_KEY"]

INDEX_CODES = ("GSPC.INDX", "MID.INDX", "SML.INDX")
MIN_RESPONSE_BYTES = 200
SYMBOL_ALIASES = {"MRP_old": "MRP", "TLN_old": "TLN"}


def resolve_universe() -> set:
    tickers = set()
    th_path = DATA_DIR / "constituents"
    th_path.mkdir(exist_ok = True)
    for x in INDEX_CODES:
        params = {"api_token": API_KEY, "fmt": "json"}
        resp = requests.get(f"https://eodhd.com/api/mp/unicornbay/spglobal/comp/{x}", params = params)
        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code} {x}")
        the_path = DATA_DIR / "constituents" / f"{x}.json"
        w = resp.json()
        with open(the_path, "w", encoding = "utf-8") as f:
            json.dump(w, f)
        for entry in w["HistoricalTickerComponents"].values():
            tickers.add(entry["Code"])
    return tickers


def prices(symbols: set) -> None:
    price_path = DATA_DIR / "prices"
    price_path.mkdir(exist_ok = True)
    requests_per_minute = 1000
    delay = 60/requests_per_minute
    failures = []
    for x in symbols:
        pr_path = DATA_DIR / "prices" / f"{x}.json"
        if pr_path.exists() and pr_path.stat().st_size > MIN_RESPONSE_BYTES:
            continue
        else:
            time.sleep(delay)
            params = {"api_token": API_KEY, "fmt": "json", "period" : "d", "from": "2017-01-01"}
            pm = requests.get(f"https://eodhd.com/api/eod/{SYMBOL_ALIASES.get(x, x)}" , params = params)
        if pm.status_code != 200:
            failures.append(x)
            continue
        z = pm.json()
        if not z:
            failures.append(x)
            continue
        with open(pr_path, "w", encoding = "utf-8") as f:
            json.dump(z, f)
    if failures:
        print(f"fetch_prices: {len(failures)} symbols returned no data: {sorted(failures)}")


def fundamentals(symbols: set) -> None:
    data_path = DATA_DIR / "fundamentals"
    data_path.mkdir(exist_ok= True)
    failures = []
    requests_per_minute = 1000
    delay = 60/requests_per_minute
    for x in symbols:
        dt_path = DATA_DIR / "fundamentals" / f"{x}.json"
        if dt_path.exists() and dt_path.stat().st_size > MIN_RESPONSE_BYTES:
            continue
        else:
            time.sleep(delay)
            params = {"api_token": API_KEY, "fmt": "json"}
            pxsd = requests.get(f"https://eodhd.com/api/fundamentals/{SYMBOL_ALIASES.get(x, x)}", params = params)
        if pxsd.status_code != 200:
            failures.append(x)
            continue
        q = pxsd.json()
        if not q:
            failures.append(x)
            continue
        with open(dt_path, "w", encoding = "utf-8") as f:
            json.dump(q, f)
    if failures:
        print(f"fetch_fundamentals: {len(failures)} symbols returned no data: {sorted(failures)}")


def pull() -> None:
    with open(DATA_DIR / "constituents" / "MID.INDX.json", encoding = "utf-8") as f:
        w = json.load(f)
    entries0 = list(w["HistoricalTickerComponents"].values())
    has_del0 = False
    for entry in entries0:
        if entry.get("EndDate") is not None:
            has_del0 = True
    with open(DATA_DIR / "constituents" / "SML.INDX.json", encoding = "utf-8") as f:
        w = json.load(f)
    entries1 = list(w["HistoricalTickerComponents"].values())
    has_del1 = False
    for entry in entries1:
        if entry.get("EndDate") is not None:
            has_del1 = True
    if has_del0 and has_del1:
        print("PASS")
    else:
        print("FAIL")

    deletions = []
    for entry in entries0 + entries1:
        if entry.get("IsDelisted") == 1 and entry["Code"] != "--":
            deletions.append(entry)
    spot_check = []
    for entry in deletions[:3]:
        spot_check.append(entry["Code"])
    ok = True
    for x in spot_check:
        price_ok = (DATA_DIR / "prices" / f"{x}.json").exists()
        fund_ok = (DATA_DIR / "fundamentals" / f"{x}.json").exists()
        if not (price_ok and fund_ok):
            ok = False
            print(f"  missing data for delisted ticker {x}")
    if ok:
        print("PASS")
    else:
        print("FAIL")

    x = "AAPL"
    fields = (
        "totalRevenue", "costOfRevenue",
        "sellingGeneralAdministrative",
    )
    ok = True
    found_year_in_window = False
    with open(DATA_DIR / "fundamentals" / f"{x}.json", encoding = "utf-8") as f:
        w = json.load(f)
    income_yearly = w.get("Financials", {}).get("Income_Statement", {}).get("yearly", {})
    for fy in income_yearly:
        values = income_yearly[fy]
        if not fy.startswith(("2019", "2020", "2021", "2022", "2023", "2024", "2025")):
            continue
        found_year_in_window = True
        for field in fields:
            if values.get(field) in (None, "None"):
                ok = False
    fields1 = ("totalStockholderEquity",
        "totalAssets", "commonStockSharesOutstanding",
    )
    ok1 = True
    found_year_in_window1 = False
    balance_yearly = w.get("Financials", {}).get("Balance_Sheet", {}).get("yearly", {})
    for fy in balance_yearly:
        values = balance_yearly[fy]
        if not fy.startswith(("2019", "2020", "2021", "2022", "2023", "2024", "2025")):
            continue
        found_year_in_window1 = True
        for field in fields1:
            if values.get(field) in (None, "None"):
                ok1 = False
    if ok and ok1 and found_year_in_window and found_year_in_window1:
        print("PASS")
    else:
        print("FAIL")

    x = "AAPL"
    with open(DATA_DIR / "prices" / f"{x}.json", encoding = "utf-8") as f:
        w = json.load(f)
    dates = []
    for row in w:
        dates.append(row["date"])
    has_ohlc = True
    for row in w:
        if (row.get("open") is None or row.get("high") is None
                or row.get("low") is None or row.get("close") is None
                or row.get("adjusted_close") is None):
            has_ohlc = False
    covers_window = min(dates) <= "2019-01-31" and max(dates) >= "2026-01-02"
    if has_ohlc and covers_window:
        print("PASS")
    else:
        print("FAIL")

    flagged = []
    for folder in (DATA_DIR / "prices", DATA_DIR / "fundamentals"):
        for path in folder.iterdir():
            if path.stat().st_size < MIN_RESPONSE_BYTES:
                flagged.append(str(path))
    if flagged:
        print(f"FAIL -- {len(flagged)} undersized files: {flagged}")
    else:
        print("PASS")


if __name__ == "__main__":
    universe = resolve_universe()
    prices(universe)
    fundamentals(universe)
    pull()
