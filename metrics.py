import pandas as pd
import pandas_datareader.data as web
import statsmodels.api as sm


def factors(start: str, end: str) -> pd.DataFrame:
    factors = web.DataReader("F-F_Research_Data_5_Factors_2x3", "famafrench", start=start, end=end)
    df = factors[0]
    df /= 100
    return df


def annualized_return(returns: pd.Series) -> float:
    n_months = len(returns)
    return (1 + returns).prod() ** (12 / n_months) - 1


def annualized_volatility(returns: pd.Series) -> float:
    return returns.std() * (12 ** 0.5)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    return (annualized_return(returns) - risk_free_rate) / annualized_volatility(returns)


def sortino_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    downside = returns.clip(upper=0)
    downside_dev = (downside**2).mean() ** 0.5 * (12 ** 0.5)
    return (annualized_return(returns) - risk_free_rate) / downside_dev


def max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    return drawdown.min()


def ff5(returns: pd.Series, ff5: pd.DataFrame):
    # HML is included in this regression as it is one of the Fama-French 5 factors, despite the fact that it was excluded from my strategy. 
    # Excess Return is calculated as this is the standard FF5 convention. 
    merged = pd.merge(returns, ff5, left_index=True, right_index=True)
    excess_return = merged["return"] - merged["RF"]
    X = sm.add_constant(merged[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]])
    return sm.OLS(excess_return, X).fit()


def compute_all_metrics(returns, ic, decile_spread, ff5_data, risk_free_rate):
    market = ff5_data["Mkt-RF"] + ff5_data["RF"] # benchmark market is the entire US equities market cap-weighted, sourced from Ken French's website
    market = market.reindex(returns.index)
    metrics = {
        "Annualized Return": annualized_return(returns),
        "Annualized Volatility": annualized_volatility(returns),
        "Sharpe Ratio": sharpe_ratio(returns, risk_free_rate),
        "Sortino Ratio": sortino_ratio(returns, risk_free_rate),
        "Max Drawdown": max_drawdown(returns),
        "Mean Information Coefficient": ic.mean(),
        "Mean Decile Spread": decile_spread.mean(),
        "Market Annualized Return": annualized_return(market),
        "Market Annualized Volatility": annualized_volatility(market),
        "Market Sharpe Ratio": sharpe_ratio(market, risk_free_rate),
        "Market Max Drawdown": max_drawdown(market)
    }
    model = ff5(returns, ff5_data)
    for name, val in model.params.items():
        if name == "const":
            metrics["FF5 Alpha (Monthly)"] = val
        else:
            metrics[f"FF5 Beta: {name}"] = val
    for name, val in model.pvalues.items():
        if name == "const":
            metrics["FF5 P-Value: Alpha"] = val
        else:
            metrics[f"FF5 P-Value: {name}"] = val
    metrics["FF5 R-Squared"] = model.rsquared
    metrics["FF5 Observations"] = model.nobs
    pd.Series(metrics, name="Value").to_csv("metrics.csv", header=True, index_label="Metric")
