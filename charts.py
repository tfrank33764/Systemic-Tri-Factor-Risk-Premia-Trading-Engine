import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, FixedLocator


def cum_return(returns: pd.Series, mkt_return: pd.Series = None, savepath: str = None) -> None:
    cumulative = (1 + returns).cumprod()
    fig, ax = plt.subplots(figsize = (10,5.5))
    ax.plot(cumulative.index, cumulative.values, label="Strategy")
    if mkt_return is not None:
        market = (1 + mkt_return).cumprod()
        ax.plot(market.index, market.values, label="Cap-Weighted US Market (Fama-French)")
    ax.set_title("Cumulative Return")
    ax.set_xlabel("Date")
    ax.set_ylabel("Growth of $1")
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator([1, 1.5, 2, 3, 4, 6, 8]))
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.axhline(1.0, color="gray", lw=0.8, ls="--", zorder=0)
    ax.legend()
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()
    plt.close(fig)


def drawdown(returns: pd.Series, savepath: str = None) -> None:
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    fig, ax = plt.subplots()
    ax.fill_between(drawdown.index, drawdown.values, 0)
    ax.set_title("Drawdown Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.set_xlim(drawdown.index[0], drawdown.index[-1])
    ax.set_ylim(top=0)
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()
    plt.close(fig)


def ret_tab(returns: pd.Series) -> pd.DataFrame:
    data = pd.DataFrame({"year": returns.index.year, "month": returns.index.month, "return": returns.values})
    return data.pivot_table(index="year", columns="month", values="return")


def heatmap(returns: pd.Series, savepath: str = None) -> None:
    table = ret_tab(returns)
    fig, ax = plt.subplots(figsize= (12, 5))
    im = ax.imshow(table.values, cmap="RdBu", aspect = "auto")
    ax.set_yticks(range(len(table.index)))
    ax.set_yticklabels(table.index)
    ax.set_xticks(range(len(table.columns)))
    ax.set_xticklabels(table.columns)
    for i in range(len(table.index)):
        for j in range(len(table.columns)):
            value = table.values[i, j]
            if pd.notna(value):
                ax.text(j, i, f"{value:.1%}", ha="center", va="center", fontsize = 7)
    fig.colorbar(im, ax=ax)
    ax.set_title("Monthly Return Heatmap")
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    if savepath:
        fig.savefig(savepath)
    else:
        plt.show()
    plt.close(fig)


def ic_series(ic: pd.Series, savepath: str = None) -> None:
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
    plt.close(fig)


def decile_series(decile_spread: pd.Series, savepath: str = None) -> None:
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
    plt.close(fig)
