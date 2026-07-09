import pandas as pd
import matplotlib.pyplot as plt


def plot_cumulative_return(returns: pd.Series, mkt_return: pd.Series = None, savepath: str = None) -> None:
    cumulative = (1 + returns).cumprod()
    fig, ax = plt.subplots()
    ax.plot(cumulative.index, cumulative.values, label="Strategy")
    if mkt_return is not None:
        market = (1 + mkt_return).cumprod()
        ax.plot(market.index, market.values, label="Market Return")
    ax.set_title("Cumulative Return")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth")
    ax.legend()
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()


def plot_drawdown(returns: pd.Series, savepath: str = None) -> None:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    fig, ax = plt.subplots()
    ax.fill_between(drawdown.index, drawdown.values, 0)
    ax.set_title("Drawdown Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()


def monthly_return_table(returns: pd.Series) -> pd.DataFrame:
    data = pd.DataFrame({"year": returns.index.year, "month": returns.index.month, "return": returns.values})
    return data.pivot_table(index="year", columns="month", values="return")


def plot_monthly_heatmap(returns: pd.Series, savepath: str = None) -> None:
    table = monthly_return_table(returns)
    fig, ax = plt.subplots()
    im = ax.imshow(table.values, cmap="RdYlGn")
    ax.set_yticks(range(len(table.index)))
    ax.set_yticklabels(table.index)
    ax.set_xticks(range(len(table.columns)))
    ax.set_xticklabels(table.columns)
    for i in range(len(table.index)):
        for j in range(len(table.columns)):
            value = table.values[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.2f}", ha="center", va="center")
    fig.colorbar(im, ax=ax)
    ax.set_title("Monthly Return Heatmap")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()


def plot_ic_time_series(ic: pd.Series, savepath: str = None) -> None:
    fig, ax = plt.subplots()
    ax.plot(ic.index, ic.values)
    ax.axhline(0, linestyle="--")
    ax.set_title("IC Time Series")
    ax.set_xlabel("Date")
    ax.set_ylabel("Information Coefficient")
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()


def plot_decile_spread_time_series(decile_spread: pd.Series, savepath: str = None) -> None:
    fig, ax = plt.subplots()
    ax.plot(decile_spread.index, decile_spread.values)
    ax.axhline(0, linestyle="--")
    ax.set_title("Decile Spread Time Series")
    ax.set_xlabel("Date")
    ax.set_ylabel("Decile Spread")
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()
