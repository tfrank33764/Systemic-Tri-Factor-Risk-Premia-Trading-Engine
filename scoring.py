import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path("data")


def add_adjusted_open(df: pd.DataFrame) -> pd.DataFrame:
    # The API used in this project does not compute an adjusted open field that accounts for occurences such as a stock split or dividend payments. 
    # Thus, if this project used the regular open field, the results would be flawed if any stock splits or similar changes occured to any stock purchased. 
    # To avoid this error, I created an adjusted open field based upon the ratio between adjusted close, which is reported by EODHD, and closed.
    # This field, which accounts for stock splits, etc. was then used in the project. 
    scalefactor = df["adjusted_close"] / df["close"]
    df["adjusted_open"] = df["open"] * scalefactor
    df["adjusted_open"] = df["adjusted_open"].replace([float("inf"), float("-inf")], float("nan"))
    return df


def monthly_returns_from_open(df: pd.DataFrame) -> pd.Series:
    monthly_opens = df["adjusted_open"].resample("MS").first()
    return monthly_opens.pct_change()


def to_float_or_nan(value):
    if value is not None:
        return float(value)
    return float("nan")


def extract_fundamentals_row(ticker: str, fiscal_year: str) -> dict:
    with open(DATA_DIR / "fundamentals" / f"{ticker}.json") as f:
        w = json.load(f)
        if (fiscal_year not in w["Financials"]["Income_Statement"]["yearly"]
                or fiscal_year not in w["Financials"]["Balance_Sheet"]["yearly"]):
            return {"revenue": float("nan"), "cogs": float("nan"), "interest_expense": float("nan"),
                    "sga": float("nan"), "book_equity": float("nan"), "total_assets": float("nan")}

    income = w["Financials"]["Income_Statement"]["yearly"][fiscal_year]
    balance = w["Financials"]["Balance_Sheet"]["yearly"][fiscal_year]

    return {
        "revenue": to_float_or_nan(income.get("totalRevenue")),
        "cogs": to_float_or_nan(income.get("costOfRevenue")),
        "interest_expense": to_float_or_nan(income.get("interestExpense")),
        "sga": to_float_or_nan(income.get("sellingGeneralAdministrative")),
        "book_equity": to_float_or_nan(balance.get("totalStockholderEquity")),
        "total_assets": to_float_or_nan(balance.get("totalAssets")),
    }


def compute_rmw(df: pd.DataFrame) -> pd.Series:
    df["Operating Income"] = df["revenue"] - df["cogs"] - df["interest_expense"].fillna(0) - df["sga"]
    df["rmw"] = df["Operating Income"] / df["book_equity"]
    df["rmw"] = df["rmw"].replace([float("inf"), float("-inf")], float("nan"))
    return df["rmw"]


def compute_cma(df: pd.DataFrame) -> pd.Series:
    df["cma"] = (df["total_assets"] - df["total_assets"].shift(1)) / df["total_assets"].shift(1)
    df["cma"] = df["cma"].replace([float("inf"), float("-inf")], float("nan"))
    return df["cma"]


def score_stocks(df: pd.DataFrame) -> pd.DataFrame:
    df["smb_score"] = df["market_cap"].rank(pct=True, ascending=False)
    df["rmw_score"] = df["rmw"].rank(pct=True, ascending=True)
    df["cma_score"] = df["cma"].rank(pct=True, ascending=False)
    df["composite"] = (df["smb_score"] + df["rmw_score"] + df["cma_score"]) / 3
    return df


def select_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["composite"] >= 0.75]


def get_market_cap(ticker: str) -> float:
    with open(DATA_DIR / "prices" / f"{ticker}.json") as f:
        w = json.load(f)
    prices = add_adjusted_open(pd.DataFrame(w))
    adjusted_open = prices["adjusted_open"].iloc[-1]

    with open(DATA_DIR / "fundamentals" / f"{ticker}.json") as f:
        w = json.load(f)
    latest_year = sorted(w["Financials"]["Balance_Sheet"]["yearly"].keys())[-1]
    shares = float(w["Financials"]["Balance_Sheet"]["yearly"][latest_year]["commonStockSharesOutstanding"])
    return adjusted_open * shares


def get_latest_rmw_cma(ticker: str, fiscal_years: list) -> dict:
    rows = []
    for fy in fiscal_years:
        row = extract_fundamentals_row(ticker, fy)
        row["year"] = fy
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(by="year")
    df["rmw"] = compute_rmw(df)
    df["cma"] = compute_cma(df)
    return {"rmw": df.iloc[-1]["rmw"], "cma": df.iloc[-1]["cma"]}
