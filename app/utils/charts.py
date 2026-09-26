import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

from app.utils.data import safe_num

# ── Design tokens ──
COLORS = {
    "bg":      "#0a0c0f",
    "surface": "#111318",
    "border":  "#1e2430",
    "green":   "#c8ff3e",
    "blue":    "#3ecfff",
    "amber":   "#ffb83e",
    "red":     "#ff4d4d",
    "text":    "#e2e8f0",
    "muted":   "#8899aa",
}

LAYOUT_BASE = dict(
    paper_bgcolor=COLORS["surface"],
    plot_bgcolor=COLORS["surface"],
    font=dict(family="DM Sans", color=COLORS["text"], size=12),
    margin=dict(l=16, r=16, t=32, b=16),
    xaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
    ),
    yaxis=dict(
        gridcolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
    ),
)


def asi_trend_chart(df: pd.DataFrame) -> go.Figure:
    """ASI 30-day trend line chart."""
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["asi"],
        mode="lines",
        line=dict(color=COLORS["green"], width=2),
        fill="tozeroy",
        fillcolor="rgba(200,255,62,0.05)",
        name="ASI",
        hovertemplate="<b>%{x}</b><br>ASI: %{y:,.2f}<extra></extra>"
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text="ASI 30-Day Trend", font=dict(size=11, color=COLORS["muted"]), x=0),
        showlegend=False,
        height=220,
    )
    return fig


def price_history_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Price history line chart for one stock."""
    if df.empty:
        return go.Figure()

    color = COLORS["blue"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["price"],
        mode="lines+markers",
        line=dict(color=color, width=2),
        marker=dict(size=4, color=color),
        fill="tozeroy",
        fillcolor="rgba(62,207,255,0.05)",
        name=symbol,
        hovertemplate="<b>%{x}</b><br>₦%{y:.2f}<extra></extra>"
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        margin=dict(l=16, r=16, t=32, b=16),
        title=dict(text=f"{symbol} — Price History", font=dict(size=11, color=COLORS["muted"]), x=0),
        showlegend=False,
        height=250,
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
            tickprefix="₦",
        ),
    )
    return fig


def score_breakdown_chart(momentum: float, dividend: float, fundamentals: float = None) -> go.Figure:
    """Horizontal bar chart showing score breakdown."""
    momentum = safe_num(momentum)
    dividend = safe_num(dividend)
    if fundamentals is not None:
        fundamentals = safe_num(fundamentals)
    labels = ["Momentum", "Dividend"]
    values = [momentum, dividend]
    colors = [COLORS["amber"], COLORS["green"]]

    if fundamentals is not None:
        labels.append("Fundamentals")
        values.append(fundamentals)
        colors.append(COLORS["blue"])

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color=colors, opacity=0.85),
        text=[f"{v:.0f}/100" for v in values],
        textposition="outside",
        textfont=dict(family="DM Mono", size=11, color=COLORS["text"]),
        hovertemplate="%{y}: %{x:.0f}/100<extra></extra>",
        width=0.5,
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        margin=dict(l=16, r=16, t=32, b=16),
        title=dict(text="Score Breakdown", font=dict(size=11, color=COLORS["muted"]), x=0),
        showlegend=False,
        height=180,
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
            range=[0, 115]
        ),
        yaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
        bargap=0.4,
    )
    return fig


def score_history_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Multi-line score history over time."""
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    traces = [
        ("combined_score", "Combined", COLORS["green"], 2.5),
        ("momentum_score", "Momentum", COLORS["amber"], 1.5),
        ("dividend_score", "Dividend", COLORS["blue"], 1.5),
    ]
    for col, name, color, width in traces:
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df["date"], y=df[col],
                mode="lines",
                name=name,
                line=dict(color=color, width=width),
                hovertemplate=f"<b>%{{x}}</b><br>{name}: %{{y:.1f}}<extra></extra>"
            ))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        margin=dict(l=16, r=16, t=32, b=16),
        title=dict(text=f"{symbol} — Score History", font=dict(size=11, color=COLORS["muted"]), x=0),
        legend=dict(
            orientation="h", x=0, y=1.15,
            font=dict(family="DM Mono", size=10, color=COLORS["muted"])
        ),
        height=220,
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
            range=[0, 105]
        ),
    )
    return fig


def fundamentals_comparison_chart(df: pd.DataFrame, metric: str, label: str, is_percent: bool = True) -> go.Figure:
    """Bar chart comparing one fundamental metric across stocks."""
    if df.empty or metric not in df.columns:
        return go.Figure()

    df_clean = df[df[metric].notna()].copy()
    if df_clean.empty:
        return go.Figure()

    df_clean = df_clean.sort_values(metric, ascending=True)
    colors = [COLORS["red"] if v < 0 else COLORS["green"] for v in df_clean[metric]]

    fig = go.Figure(go.Bar(
        x=df_clean[metric],
        y=df_clean["symbol"],
        orientation="h",
        marker=dict(color=colors, opacity=0.85),
        text=[f"{v:.1f}%" if is_percent else f"{v:.2f}" for v in df_clean[metric]],
        textposition="outside",
        textfont=dict(family="DM Mono", size=10, color=COLORS["text"]),
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>" if is_percent else "%{y}: %{x:.2f}<extra></extra>",
        width=0.6,
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        margin=dict(l=16, r=16, t=32, b=16),
        title=dict(text=label, font=dict(size=11, color=COLORS["muted"]), x=0),
        showlegend=False,
        height=max(180, len(df_clean) * 40),
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
            ticksuffix="%" if is_percent else ""
        ),
        yaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
    )
    
    return fig


def volume_chart(df: pd.DataFrame, symbol: str) -> go.Figure:
    """Volume bar chart."""
    if df.empty:
        return go.Figure()

    fig = go.Figure(go.Bar(
        x=df["date"],
        y=df["volume"],
        marker=dict(color=COLORS["blue"], opacity=0.6),
        hovertemplate="<b>%{x}</b><br>Vol: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["surface"],
        plot_bgcolor=COLORS["surface"],
        font=dict(family="DM Sans", color=COLORS["text"], size=12),
        margin=dict(l=16, r=16, t=32, b=16),
        title=dict(text=f"{symbol} — Volume", font=dict(size=11, color=COLORS["muted"]), x=0),
        showlegend=False,
        height=150,
        xaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
        yaxis=dict(
            gridcolor=COLORS["border"],
            linecolor=COLORS["border"],
            tickfont=dict(family="DM Mono", size=10, color=COLORS["muted"]),
        ),
    )
    return fig