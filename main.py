import pandas as pd

from backtest import run
from metrics import compute_all_metrics, factors
from charts import (
    cum_return,
    drawdown,
    heatmap,
    ic_series,
    decile_series,
)

if __name__ == "__main__":
    df = run()
    df.to_csv("backtest_results.csv", index=False)

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    returns = df["return"]

    ff5 = factors("2019-01-01", "2025-12-31")
    monthly_rf = ff5["RF"].mean() # chosen RF rate is Ken French's 1 month T-bill
    annual_rf = (1 + monthly_rf) ** 12 - 1

    raw_market = ff5["Mkt-RF"] + ff5["RF"]
    raw_market.index = raw_market.index.to_timestamp()
    raw_market = raw_market.reindex(returns.index)

    returns_by_period = returns.copy()
    returns_by_period.index = returns_by_period.index.to_period("M")
    ff5_for_regression = ff5.copy()

    compute_all_metrics(returns_by_period, df["ic"], df["decile_spread"], ff5_for_regression, annual_rf)

    cum_return(returns, mkt_return=raw_market, savepath="charts/cumulative_return.png")
    drawdown(returns, savepath="charts/drawdown.png")
    heatmap(returns, savepath="charts/monthly_heatmap.png")
    ic_series(df["ic"], savepath="charts/ic_time_series.png")
    decile_series(df["decile_spread"], savepath="charts/decile_spread_time_series.png")

    print("done")
