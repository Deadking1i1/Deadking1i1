from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "generated"
USER = os.environ.get("GITHUB_USER", "Deadking1i1")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
COLORS = {
    "bg": "#050505",
    "panel": "#0b0d0f",
    "red_dark": "#8b0000",
    "red": "#dc143c",
    "hot": "#ff1744",
    "silver": "#c0c0c0",
    "text": "#e5e7eb",
    "muted": "#7d8590",
}


def request_json(url: str, *, data: dict | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ShadowBlue-Profile-Metrics",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    payload = json.dumps(data).encode() if data is not None else None
    request = Request(url, data=payload, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def frame(title: str, subtitle: str, width: int, height: int, content: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(subtitle)}</desc>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="7" fill="{COLORS['bg']}" stroke="#4c525b"/>
  <path d="M14 50V14h36M{width - 50} 14h36v36M14 {height - 50}v36h36M{width - 50} {height - 14}h36v-36" fill="none" stroke="{COLORS['red_dark']}" stroke-width="2"/>
  <text x="28" y="34" fill="{COLORS['red']}" font-family="Consolas,monospace" font-size="12" letter-spacing="3">{escape(title.upper())}</text>
  {content}
</svg>'''


def text(x: float, y: float, value: str, *, size: int = 14, fill: str | None = None, anchor: str = "start", weight: int = 400, spacing: int = 0) -> str:
    return f'<text x="{x}" y="{y}" fill="{fill or COLORS["text"]}" text-anchor="{anchor}" font-family="Consolas,monospace" font-size="{size}" font-weight="{weight}" letter-spacing="{spacing}">{escape(str(value))}</text>'


def generate() -> None:
    OUTPUT.mkdir(exist_ok=True)
    profile = request_json(f"{API}/users/{USER}")
    repos = request_json(f"{API}/users/{USER}/repos?per_page=100&type=owner&sort=updated")
    public_repos = [repo for repo in repos if not repo.get("fork")]
    stars = sum(repo.get("stargazers_count", 0) for repo in public_repos)

    stat_items = [
        ("PUBLIC REPOSITORIES", profile.get("public_repos", len(public_repos))),
        ("FOLLOWERS", profile.get("followers", 0)),
        ("FOLLOWING", profile.get("following", 0)),
        ("STARS RECEIVED", stars),
    ]
    stats_content = []
    for index, (label, value) in enumerate(stat_items):
        x = 34 + (index % 2) * 272
        y = 78 + (index // 2) * 58
        stats_content.append(text(x, y, label, size=10, fill=COLORS["muted"], spacing=1))
        stats_content.append(text(x, y + 27, str(value), size=23, fill=COLORS["text"], weight=700))
        stats_content.append(f'<circle cx="{x + 220}" cy="{y + 18}" r="4" fill="{COLORS["hot"]}"/>')
    stats_content.append(text(546, 164, f"SYNC {datetime.now(timezone.utc):%Y-%m-%d UTC}", size=9, fill=COLORS["muted"], anchor="end"))
    (OUTPUT / "stats.svg").write_text(frame("System telemetry", "Current public GitHub account statistics.", 580, 180, "".join(stats_content)), encoding="utf-8")

    language_totals: dict[str, int] = {}
    for repo in public_repos:
        languages = request_json(repo["languages_url"])
        for language, count in languages.items():
            language_totals[language] = language_totals.get(language, 0) + count
    top_languages = sorted(language_totals.items(), key=lambda item: item[1], reverse=True)[:5]
    total_bytes = sum(language_totals.values()) or 1
    language_content = []
    for index, (language, count) in enumerate(top_languages):
        y = 67 + index * 24
        percent = count / total_bytes * 100
        language_content.append(text(34, y, language, size=12))
        language_content.append(f'<rect x="175" y="{y - 10}" width="320" height="8" rx="4" fill="#17191d"/>')
        language_content.append(f'<rect x="175" y="{y - 10}" width="{max(2, 320 * percent / 100):.1f}" height="8" rx="4" fill="{COLORS["red"]}"/>')
        language_content.append(text(546, y, f"{percent:.1f}%", size=11, fill=COLORS["silver"], anchor="end"))
    (OUTPUT / "languages.svg").write_text(frame("Language matrix", "Languages aggregated from public non-fork repositories by GitHub-reported byte count.", 580, 180, "".join(language_content)), encoding="utf-8")

    contribution_content = generate_contributions()
    (OUTPUT / "activity.svg").write_text(frame("Contribution activity", "Daily contribution counts for the last year from GitHub's GraphQL API.", 1200, 240, contribution_content), encoding="utf-8")


def generate_contributions() -> str:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=364)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionCount date weekday } }
          }
        }
      }
    }
    """
    result = request_json(
        "https://api.github.com/graphql",
        data={"query": query, "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()}},
    )
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {result['errors']}")
    calendar = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"][-53:]
    counts = [day["contributionCount"] for week in weeks for day in week["contributionDays"]]
    maximum = max(counts, default=1)
    cells = []
    x0, y0, cell, gap = 58, 82, 14, 4
    shades = ["#15171a", "#3b000b", "#720016", COLORS["red"], COLORS["hot"]]
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            level = 0 if count == 0 else min(4, 1 + int((count / maximum) * 3))
            x = x0 + week_index * (cell + gap)
            y = y0 + day["weekday"] * (cell + gap)
            cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{shades[level]}"><title>{count} contributions on {day["date"]}</title></rect>')
    labels = [text(30, y0 + 11, "SUN", size=8, fill=COLORS["muted"]), text(30, y0 + 3 * (cell + gap) + 11, "WED", size=8, fill=COLORS["muted"]), text(30, y0 + 6 * (cell + gap) + 11, "SAT", size=8, fill=COLORS["muted"])]
    labels.append(text(1140, 35, f"{calendar['totalContributions']} CONTRIBUTIONS / 365D", size=11, fill=COLORS["silver"], anchor="end", spacing=1))
    labels.append(text(1140, 222, f"LIVE GITHUB DATA · UPDATED {datetime.now(timezone.utc):%Y-%m-%d UTC}", size=9, fill=COLORS["muted"], anchor="end"))
    return "".join(labels + cells)


if __name__ == "__main__":
    generate()
    print(f"Generated profile metrics for {USER} in {OUTPUT}")
