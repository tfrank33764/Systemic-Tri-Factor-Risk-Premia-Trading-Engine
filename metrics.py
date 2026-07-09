import pandas as pd
import pandas_datareader.data as web
import statsmodels.api as sm


def fetch_ff5_factors(start: str, end: str) -> pd.DataFrame:
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
    downside = returns[returns < 0]
    downside_dev = downside.std() * (12 ** 0.5)
    return (annualized_return(returns) - risk_free_rate) / downside_dev


def max_drawdown(returns: pd.Series) -> float:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    return drawdown.min()


def ff5_regression(returns: pd.Series, ff5: pd.DataFrame):
    # HML is included in this regression as it is one of the Fama-French 5 factors, despite the fact that it was excluded from my strategy because it has been rendered rather obsolete by RMW and CMA. 
    # Excess Return is calculated as this is the standard FF5 convention. 
    merged = pd.merge(returns, ff5, left_index=True, right_index=True)
    excess_return = merged["return"] - merged["RF"]
    X = sm.add_constant(merged[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]])
    return sm.OLS(excess_return, X).fit()


def mean_information_coefficient(ic: pd.Series) -> float:
    return ic.mean()


def mean_decile_spread(decile_spread: pd.Series) -> float:
    return decile_spread.mean()


def compute_all_metrics(returns, ic, decile_spread, ff5, risk_free_rate):
    metrics = {
        "annualized_return": annualized_return(returns),
        "annualized volatility": annualized_volatility(returns),
        "sharpe ratio": sharpe_ratio(returns, risk_free_rate),
        "Sortino Ratio": sortino_ratio(returns, risk_free_rate),
        "Max Drawdown": max_drawdown(returns),
        "Mean Information Coefficient": mean_information_coefficient(ic),
        "Mean Decile Spread": mean_decile_spread(decile_spread),
    }
    model = ff5_regression(returns, ff5)
    betas = {f"FF5 beta: {name}": val for name, val in model.params.items()}
    pvals = {f"FF5 pvalue: {name}": val for name, val in model.pvalues.items()}
    metrics.update(betas)
    metrics.update(pvals)
    pd.Series(metrics, name="Value").to_csv("metrics.csv", header=True, index_label="Metric")
