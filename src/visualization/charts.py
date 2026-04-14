"""Data Visualizations for Better Call Scout (Person 2: Sindhuja).

Four charts rendered as PNG bytes:
- star_velocity_chart: top-10 repos, star velocity over simulated weeks
- category_heatmap: tech categories x weeks, color = mean star velocity
- hn_buzz_scatter: HN score vs GitHub stars scatter
- persona_score_bars: side-by-side analyst confidence scores per repo
"""
import io
import random

import matplotlib
matplotlib.use("Agg")  # Must be first — before any pyplot import
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from src.models.schemas import AnalystHypothesis, RepoData, SynthesisReport


def _fig_to_png(fig: plt.Figure) -> bytes:
    """Serialize a matplotlib Figure to PNG bytes and close it.

    Args:
        fig: The Figure to serialize.

    Returns:
        PNG bytes.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    plt.close(fig)  # Prevent memory leaks in long-running processes
    return buf.getvalue()


def star_velocity_chart(report: SynthesisReport) -> bytes:
    """Render a line chart of star velocity for the top 10 repos (VIZ-01).

    Simulates weekly star velocity by adding small noise to each repo's
    star_velocity value across 6 weeks. Real week-over-week data will be
    wired in Phase 4 when the collection layer provides historical data.

    Args:
        report: SynthesisReport containing top_repos with star_velocity values.

    Returns:
        PNG image as bytes.
    """
    repos = report.top_repos[:10]
    weeks = list(range(1, 7))

    random.seed(42)

    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(12, 6))

    for repo in repos:
        # Simulate 6 weekly data points via random walk from base velocity
        values = [repo.star_velocity]
        for _ in range(5):
            noise = random.uniform(-0.05, 0.05)
            next_val = max(-1.0, min(1.0, values[-1] + noise))
            values.append(next_val)
        short_name = repo.name.split("/")[-1] if "/" in repo.name else repo.name
        ax.plot(weeks, values, marker="o", label=short_name)

    ax.set_xlabel("Week")
    ax.set_ylabel("Star Velocity")
    ax.set_title("Star Velocity Trend — Top Repos")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", borderaxespad=0.0)
    ax.set_xticks(weeks)
    ax.set_xticklabels([f"Week {w}" for w in weeks])

    return _fig_to_png(fig)


def category_heatmap(report: SynthesisReport) -> bytes:
    """Render a heatmap of star velocity by tech category over simulated weeks (VIZ-02).

    Args:
        report: SynthesisReport containing top_repos with topics and star_velocity.

    Returns:
        PNG image as bytes.
    """
    repos = report.top_repos

    # Collect all unique topics across repos
    all_topics: list[str] = []
    for repo in repos:
        for topic in repo.topics:
            if topic not in all_topics:
                all_topics.append(topic)

    if not repos or not all_topics:
        # Return a PNG with "No data available" text
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.text(
            0.5, 0.5, "No data available",
            ha="center", va="center", fontsize=16,
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        return _fig_to_png(fig)

    weeks = [f"Week {w}" for w in range(1, 7)]
    random.seed(42)

    # Build dict: topic -> list of weekly mean velocities
    topic_weekly: dict[str, list[float]] = {}
    for topic in all_topics:
        topic_repos = [r for r in repos if topic in r.topics]
        weekly_vals = []
        for _ in weeks:
            mean_vel = sum(r.star_velocity for r in topic_repos) / len(topic_repos)
            noise = random.uniform(-0.03, 0.03)
            weekly_vals.append(round(mean_vel + noise, 4))
        topic_weekly[topic] = weekly_vals

    df = pd.DataFrame(topic_weekly, index=weeks).T
    df.columns = weeks

    fig, ax = plt.subplots(figsize=(14, 8))
    sns.heatmap(
        df,
        ax=ax,
        cmap="YlOrRd",
        annot=True,
        fmt=".2f",
        linewidths=0.5,
    )
    ax.set_title("Category Star Velocity Heatmap")
    ax.set_xlabel("Week")
    ax.set_ylabel("Tech Category")

    return _fig_to_png(fig)


def buzz_scatter(report: SynthesisReport, news_scores: dict[str, float] | None = None) -> bytes:
    """Render a scatter plot of news buzz score vs GitHub stars (VIZ-03).

    Args:
        report: SynthesisReport containing top_repos.
        news_scores: Optional dict mapping repo name to its buzz score.
            If None, uses a synthetic score derived from star_velocity.

    Returns:
        PNG image as bytes.
    """
    repos = report.top_repos

    if not repos:
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=16, transform=ax.transAxes)
        ax.set_axis_off()
        return _fig_to_png(fig)

    data = []
    for repo in repos:
        if news_scores and repo.name in news_scores:
            hn_score = news_scores[repo.name]
        else:
            # Synthetic proxy from star_velocity
            hn_score = min(1.0, max(0.0, (repo.star_velocity + 1) / 2))
        short_name = repo.name.split("/")[-1] if "/" in repo.name else repo.name
        data.append({
            "name": short_name,
            "stars": repo.stars,
            "hn_score": hn_score,
            "star_velocity": repo.star_velocity,
        })

    df = pd.DataFrame(data)

    # Normalize star_velocity to positive sizes for scatter plot
    size_values = ((df["star_velocity"] + 1) / 2 * 400 + 50).clip(lower=50)

    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(
        df["stars"],
        df["hn_score"],
        s=size_values,
        alpha=0.7,
        c=range(len(df)),
        cmap="tab10",
    )

    # Label each point
    for _, row in df.iterrows():
        ax.annotate(
            row["name"],
            xy=(row["stars"], row["hn_score"]),
            xytext=(5, 5),
            textcoords="offset points",
            fontsize=8,
        )

    ax.set_xlabel("GitHub Stars")
    ax.set_ylabel("News Buzz Score")
    ax.set_title("News Buzz vs GitHub Stars")
    ax.set_ylim(0, 1.1)

    return _fig_to_png(fig)


def persona_score_bars(report: SynthesisReport) -> bytes:
    """Render side-by-side confidence score bars for each analyst persona (VIZ-04).

    Args:
        report: SynthesisReport containing hypotheses from all analyst personas.

    Returns:
        PNG image as bytes.
    """
    if not report.hypotheses:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.text(0.5, 0.5, "No hypotheses available", ha="center", va="center", fontsize=16, transform=ax.transAxes)
        ax.set_axis_off()
        return _fig_to_png(fig)

    data = [
        {"persona": h.persona.replace("_", " ").title(), "confidence_score": h.confidence_score}
        for h in report.hypotheses
    ]
    df = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = sns.barplot(
        data=df,
        x="persona",
        y="confidence_score",
        hue="persona",
        palette="Blues_d",
        legend=False,
        ax=ax,
    )

    # Add uncertainty threshold reference line
    ax.axhline(y=0.5, color="red", linestyle="--", linewidth=1.5, label="Uncertainty threshold (0.5)")

    # Add value labels above each bar
    ax.bar_label(ax.containers[0], fmt="%.2f", padding=3)

    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel("Analyst Persona")
    ax.set_ylabel("Confidence Score")
    ax.set_title("Analyst Confidence Scores")
    ax.legend()

    return _fig_to_png(fig)


__all__ = ["star_velocity_chart", "category_heatmap", "buzz_scatter", "persona_score_bars"]
