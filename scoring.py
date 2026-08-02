import json
from pathlib import Path
import pandas as pd


DATA_DIR = Path("data")
def adjusted_open(df: pd.DataFrame) -> pd.DataFrame:
    # The API used in this project does not compute an adjusted open field that accounts for occurences such as a stock split or dividend payments. 
    # Thus, if this project used the regular open field, the results would be flawed if any stock splits or similar changes occured to any stock purchased. 
    # To avoid this error, I created an adjusted open field based upon the ratio between adjusted close, which is reported by EODHD, and closed.
    # This field, which accounts for stock splits, etc. was then used in the project.
    #  
    scalefactor = df["adjusted_close"] / df["close"]
    df["adjusted_open"] = df["open"] * scalefactor
    df["adjusted_open"] = df["adjusted_open"].replace([float("inf"), float("-inf")], float("nan"))

    # I found a few mistaken acquisition prices which were distorting returns (ex. +1,116%)
    # These lines prevent against this, by dropping the price of tickers if they increased or decreased by a factor of 5, leading to them being excluded from return calculations. 
    traded = df["adjusted_open"].dropna()
    if len(traded) > 1 and (traded.iloc[-1] > 5 * traded.iloc[-2] or traded.iloc[-1] < traded.iloc[-2]/5): 
        df.loc[traded.index[-1], "adjusted_open"] = float("nan")

    # When a company files Chapter 11 and restructures, their old shares are voided and new shares are reissued. This was not accounted for in EODHD data.
    # Similar to the mistaken acquisition prices above, this was leading to extreme returns (+11,406%) when these shares are really worthless. 
    # To account for this, I dropped all prior trading prices following days when stocks changed by a factor of 10 or greater. 
    daily = df["adjusted_open"] / df["adjusted_open"].shift(1)
    splices = daily[(daily > 10) | (daily < 0.1)]
    if not splices.empty:
        df.loc[df.index < splices.index[-1], "adjusted_open"] = float("nan")
    return df


def monthly_returns_open(df: pd.DataFrame) -> pd.Series:
    monthly_opens = df["adjusted_open"].resample("MS").first()
    traded = df["adjusted_open"].dropna()
    if traded.empty: 
        return monthly_opens.pct_change()
    exit_date = monthly_opens.index[-1] + pd.DateOffset(months = 1)
    monthly_opens.loc[exit_date] = traded.iloc[-1]
    return monthly_opens.pct_change()


def float_nan(value):
    if value not in (None, "", "None"):
        return float(value)
    return float("nan")


def extract_fundamentals(ticker: str, fiscal_year: str) -> dict:
    with open(DATA_DIR / "fundamentals" / f"{ticker}.json", encoding="utf-8") as f:
        w = json.load(f)
        if (fiscal_year not in w["Financials"]["Income_Statement"]["yearly"]
                or fiscal_year not in w["Financials"]["Balance_Sheet"]["yearly"]):
            return {"revenue": float("nan"), "cogs": float("nan"), "interest_expense": float("nan"),
                    "sga": float("nan"), "book_equity": float("nan"), "total_assets": float("nan")}

    income = w["Financials"]["Income_Statement"]["yearly"][fiscal_year]
    balance = w["Financials"]["Balance_Sheet"]["yearly"][fiscal_year]

    return {
        "revenue": float_nan(income.get("totalRevenue")),
        "cogs": float_nan(income.get("costOfRevenue")),
        "interest_expense": float_nan(income.get("interestExpense")),
        "sga": float_nan(income.get("sellingGeneralAdministrative")),
        "book_equity": float_nan(balance.get("totalStockholderEquity")),
        "total_assets": float_nan(balance.get("totalAssets")),
    }


def rmw(df: pd.DataFrame) -> pd.Series:
    df["Operating Income"] = df["revenue"] - df["cogs"] - df["interest_expense"].fillna(0) - df["sga"] # interest expense if null is filled with zero rather than causing failure as a company could be debt free and thus not pay interest
    df["rmw"] = df["Operating Income"] / df["book_equity"].where(df["book_equity"]>0)
    df["rmw"] = df["rmw"].replace([float("inf"), float("-inf")], float("nan"))
    return df["rmw"]


def cma(df: pd.DataFrame) -> pd.Series:
    df["cma"] = (df["total_assets"] - df["total_assets"].shift(1)) / df["total_assets"].shift(1)
    df["cma"] = df["cma"].replace([float("inf"), float("-inf")], float("nan"))
    return df["cma"]


def score_stocks(df: pd.DataFrame) -> pd.DataFrame:
    df["smb_score"] = df["market_cap"].rank(pct=True, ascending=False) # ascending = false because small cap stocks are preferred
    df["rmw_score"] = df["rmw"].rank(pct=True, ascending=True) # ascending = true, robust operating profitability preferred
    df["cma_score"] = df["cma"].rank(pct=True, ascending=False) # ascending = false, low YoY growth in total assets is preferred
    df["composite"] = (df["smb_score"] + df["rmw_score"] + df["cma_score"]) / 3 # I chose for all three factors to be weighted equally in the composite
    return df


def build_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["composite"].rank(pct=True) >= 0.75] # builds the portfolio, selecting the top quartile of stocks


def get_latest_rmw_cma(ticker: str, fiscal_years: list) -> dict:
    rows = []
    for fy in fiscal_years:
        row = extract_fundamentals(ticker, fy)
        row["year"] = fy
        rows.append(row)
    df = pd.DataFrame(rows).sort_values(by="year")
    df["rmw"] = rmw(df)
    df["cma"] = cma(df)
    return {"rmw": df.iloc[-1]["rmw"], "cma": df.iloc[-1]["cma"]}
