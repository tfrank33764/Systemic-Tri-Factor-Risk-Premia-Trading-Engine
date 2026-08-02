import json
from pathlib import Path

import pandas as pd
from scipy import stats

from scoring import (
    adjusted_open,
    get_latest_rmw_cma,
    monthly_returns_open,
    score_stocks,
    build_portfolio,
    float_nan,
)

DATA_DIR = Path("data")
INDEX_FILES = ["GSPC.INDX.json", "MID.INDX.json", "SML.INDX.json"]


def load_univ() -> list:
    lst = []
    for index in INDEX_FILES:
        with open(DATA_DIR / "constituents" / index, encoding="utf-8") as f:
            w = json.load(f)
        for entry in w["HistoricalTickerComponents"].values():
            lst.append({"ticker": entry["Code"], "start": entry["StartDate"], "end": entry["EndDate"]})
    return lst


def univ_date(history: list, as_of_date: str) -> set:
    # This function prevents survivorship bias. By creating the tradable universe based upon the rebalance date, delisted stocks are included, and stocks that haven't yet become publicly traded or a member of the S&P 1500 are excluded. 
    s = set()
    for dt in history:
        if (dt["start"] is None or dt["start"] <= as_of_date) and (dt["end"] is None or dt["end"] >= as_of_date):
            s.add(dt["ticker"])
    return s


def get_rebalance_dates() -> list:
    dttm = pd.date_range(start="2019-01-01", end="2026-01-01", freq="MS") # This last rebalance date exists solely to close the last month's forward positions.
    return list(dttm.strftime("%Y-%m-%d"))


def fy_for_rebalance(rebalance_date: str) -> str:
    # This function ensures that this project follows the conventional Fama-French delay required for company disclosures to be released in real-life (6-months). This is done to prevent look-ahead bias, where trading is done based upon future information relative to the rebalance date. 
    yr = int(rebalance_date[:4])
    mth = int(rebalance_date[5:7])
    if mth >= 7:
        return str(yr - 1)
    return str(yr - 2)


def cap_on_date(ticker: str, as_of_date: str) -> float:
    with open(DATA_DIR / "prices" / f"{ticker}.json", encoding="utf-8") as f:
        w = json.load(f)
        if not w:
            return float("nan")
    prices = adjusted_open(pd.DataFrame(w).sort_values("date"))
    asof = prices[prices["date"] >= as_of_date]
    if asof.empty:
        return float("nan")
    row = asof.iloc[0]
    if pd.Timestamp(row["date"]) - pd.Timestamp(as_of_date) > pd.Timedelta(days=7):
        return float("nan")
    adj_open = row["adjusted_open"]
    with open(DATA_DIR / "fundamentals" / f"{ticker}.json", encoding="utf-8") as f:
        w = json.load(f)
    if "Financials" not in w:
        return float("nan")
    lag = fy_for_rebalance(as_of_date)
    valid_years = [k for k in w["Financials"]["Balance_Sheet"]["yearly"].keys() if k[:4] <= lag]
    if not valid_years:
        return float("nan")
    latest_year = max(valid_years)
    if int(lag) - int(latest_year[:4]) > 2:
        return float("nan")
    shares = float_nan(w["Financials"]["Balance_Sheet"]["yearly"][latest_year]["commonStockSharesOutstanding"])
    return adj_open * shares 


def rmw_cma_yr(ticker: str, calendar_year: str) -> dict:
    with open(DATA_DIR / "fundamentals" / f"{ticker}.json", encoding="utf-8") as f:
        w = json.load(f)
        if "Financials" not in w:
            return {"rmw": float("nan"), "cma": float("nan")}

    keys = list(w["Financials"]["Balance_Sheet"]["yearly"].keys())
    matches = [k for k in keys if k[:4] <= calendar_year]
    if not matches:
        return {"rmw": float("nan"), "cma": float("nan")}

    latest_year = max(matches)
    if int(calendar_year) - int(latest_year[:4]) > 2:
        return {"rmw": float("nan"), "cma": float("nan")}

    sorted_keys = sorted(keys)
    position = sorted_keys.index(latest_year)
    if position == 0:
        return {"rmw": float("nan"), "cma": float("nan")}

    prior_key = sorted_keys[position - 1]
    if int(latest_year[:4]) - int(prior_key[:4]) != 1:
        return {"rmw": float("nan"), "cma": float("nan")}

    return get_latest_rmw_cma(ticker, [prior_key, latest_year])


def monthly_ret(tickers: set) -> dict:
    ret = {}
    for ticker in tickers:
        with open(DATA_DIR / "prices" / f"{ticker}.json", encoding="utf-8") as f:
            w = json.load(f)
            if not w:
                continue
        df = pd.DataFrame(w)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        df = adjusted_open(df)
        ret[ticker] = monthly_returns_open(df)
    return ret


def factor_table(tickers: set, rebalance_date: str, rmw_cma_cache: dict) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        cap = cap_on_date(ticker, rebalance_date)
        rc = rmw_cma_cache[ticker]
        rows.append({"ticker": ticker, "market_cap": cap, "rmw": rc["rmw"], "cma": rc["cma"]})
    return pd.DataFrame(rows)


def portfolio_turnover(current_holdings: set, previous_holdings: set) -> float:
    if not current_holdings:
        return 0.0
    if not previous_holdings: 
        return 1.0
    sold = previous_holdings - current_holdings
    bought = current_holdings - previous_holdings
    return len(sold) / len(previous_holdings) + len(bought) / len(current_holdings)


def run() -> pd.DataFrame:
    history = load_univ()
    dates = get_rebalance_dates()

    all_tickers = set()
    for d in dates:
        all_tickers |= univ_date(history, d)
    returns_by_ticker = monthly_ret(all_tickers)

    last_fiscal_year = None
    rmw_cma_cache = {}
    prev_holdings = set()
    results = []

    for i in range(len(dates) - 1):
        rebalance_date = dates[i]
        next_date = dates[i + 1]
        universe = univ_date(history, rebalance_date)

        # This block enforces the annual RMW/CMA refresh while otherwise holding those values frozen, with the exception of newly added tickers which need its first fetch even mid cycle so that there is a number for selection criteria this month. 
        fiscal_year = fy_for_rebalance(rebalance_date)
        if fiscal_year != last_fiscal_year:
            last_fiscal_year = fiscal_year
            for ticker in universe:
                rc = rmw_cma_yr(ticker, fiscal_year)
                rmw_cma_cache[ticker] = {**rc, "fiscal_year": fiscal_year}
        else:
            for ticker in universe:
                if ticker not in rmw_cma_cache or rmw_cma_cache[ticker]["fiscal_year"] != fiscal_year:
                    rc = rmw_cma_yr(ticker, fiscal_year)
                    rmw_cma_cache[ticker] = {**rc, "fiscal_year": fiscal_year}

        factor_df = factor_table(universe, rebalance_date, rmw_cma_cache)
        scored = score_stocks(factor_df)

        forward_returns = []
        for ticker in scored["ticker"]:
            if ticker in returns_by_ticker:
                forward_returns.append(returns_by_ticker[ticker].get(pd.Timestamp(next_date), float("nan")))
            else:
                forward_returns.append(float("nan"))
        scored["forward_return"] = forward_returns

        valid = scored.dropna(subset=["forward_return", "composite"]).copy()
        ic, _ = stats.spearmanr(valid["composite"], valid["forward_return"])
        valid["decile"] = pd.qcut(valid["composite"], 10, labels=False, duplicates="drop")
        top, bottom = valid["decile"].max(), valid["decile"].min()
        spread = (valid.loc[valid["decile"] == top, "forward_return"].mean()
                  - valid.loc[valid["decile"] == bottom, "forward_return"].mean())

        portfolio = build_portfolio(scored)
        portfolio_return = portfolio["forward_return"].mean()
        current_holdings = set(portfolio["ticker"])
        turnover = portfolio_turnover(current_holdings, prev_holdings)
        net_return = portfolio_return - turnover * 0.0010 # 10bps assumption chosen for rebalancing, likely underestimates true costs especially on small caps. 

        results.append({
            "date": rebalance_date,
            "return": net_return,
            "ic": ic,
            "decile_spread": spread,
            "turnover": turnover,
            "n_holdings": len(current_holdings),
            "holdings_missing_return": int(portfolio["forward_return"].isna().sum()),
        })
        prev_holdings = current_holdings

    return pd.DataFrame(results)
