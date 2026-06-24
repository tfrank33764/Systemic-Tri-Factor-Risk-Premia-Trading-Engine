import pandas as pd

from backtest import run_backtest
from metrics import compute_all_metrics, fetch_ff5_factors
from charts import (
    plot_cumulative_return,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_ic_time_series,
    plot_decile_spread_time_series,
)

if __name__ == "__main__":
    df = run_backtest()
    df.to_csv("backtest_results.csv", index=False)

    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    returns = df["return"]

    ff5 = fetch_ff5_factors("2019-01-01", "2025-12-31")
    monthly_rf = ff5["RF"].mean()
    annual_rf = (1 + monthly_rf) ** 12 - 1

    raw_market = ff5["Mkt-RF"] + ff5["RF"]
    raw_market.index = raw_market.index.to_timestamp()

    returns_by_period = returns.copy()
    returns_by_period.index = returns_by_period.index.to_period("M")
    ff5_for_regression = ff5.copy()

    compute_all_metrics(returns_by_period, df["ic"], df["decile_spread"], ff5_for_regression, annual_rf)

    plot_cumulative_return(returns, mkt_return=raw_market, savepath="charts/cumulative_return.png")
    plot_drawdown(returns, savepath="charts/drawdown.png")
    plot_monthly_heatmap(returns, savepath="charts/monthly_heatmap.png")
    plot_ic_time_series(df["ic"], savepath="charts/ic_time_series.png")
    plot_decile_spread_time_series(df["decile_spread"], savepath="charts/decile_spread_time_series.png")

    print("Done. metrics.csv and charts/ written.")
