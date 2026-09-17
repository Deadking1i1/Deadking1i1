from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "generated"
DATA = ROOT / "data"
CONFIG_PATH = DATA / "repository-config.json"
REPOSITORIES_PATH = DATA / "repositories.json"
USER = os.environ.get("GITHUB_USER", "Deadking1i1")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
MISSING_DESCRIPTION = "No repository description provided."
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


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {
        "ignoreRepositories",
        "featuredRepositories",
        "includeForks",
        "includeArchived",
        "includeEmpty",
        "excludeFeaturedFromRecent",
        "maxRecentRepositories",
    }
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Repository config is missing: {', '.join(missing)}")
    if not 1 <= int(config["maxRecentRepositories"]) <= 8:
        raise ValueError("maxRecentRepositories must be between 1 and 8")
    return config


def fetch_repositories() -> list[dict]:
    repositories: list[dict] = []
    for page in range(1, 11):
        query = urlencode({"per_page": 100, "page": page, "type": "owner", "sort": "updated"})
        batch = request_json(f"{API}/users/{USER}/repos?{query}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
    return repositories


def normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_previous_detection_times() -> dict[str, str]:
    if not REPOSITORIES_PATH.exists():
        return {}
    try:
        previous = json.loads(REPOSITORIES_PATH.read_text(encoding="utf-8"))
        return {item["name"].casefold(): item["firstDetectedAt"] for item in previous.get("repositories", [])}
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def repository_is_included(repo: dict, config: dict) -> bool:
    ignored = {name.casefold() for name in config["ignoreRepositories"]}
    if repo["name"].casefold() in ignored:
        return False
    if repo.get("private", False):
        return False
    if repo.get("fork", False) and not config["includeForks"]:
        return False
    if repo.get("archived", False) and not config["includeArchived"]:
        return False
    if repo.get("size", 0) == 0 and not config["includeEmpty"]:
        return False
    return not any(re.search(pattern, repo["name"], re.IGNORECASE) for pattern in config.get("ignorePatterns", []))


def build_repository_data(repositories: list[dict], config: dict, now: datetime) -> tuple[list[dict], list[str]]:
    previous_detection = read_previous_detection_times()
    featured_names = {normalized_name(name) for name in config["featuredRepositories"]}
    discovered = []
    resolved_featured = set()

    for repo in repositories:
        if not repository_is_included(repo, config):
            continue
        is_featured = normalized_name(repo["name"]) in featured_names
        if is_featured:
            resolved_featured.add(normalized_name(repo["name"]))
        created_at = parse_time(repo["created_at"])
        detected_at = previous_detection.get(repo["name"].casefold(), now.isoformat())
        discovered.append(
            {
                "name": repo["name"],
                "fullName": repo["full_name"],
                "url": repo["html_url"],
                "description": repo.get("description") or MISSING_DESCRIPTION,
                "primaryLanguage": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "openIssues": repo.get("open_issues_count", 0),
                "createdAt": repo["created_at"],
                "updatedAt": repo["updated_at"],
                "pushedAt": repo.get("pushed_at"),
                "firstDetectedAt": detected_at,
                "isNew": now - created_at <= timedelta(days=7),
                "isFeatured": is_featured,
                "archived": repo.get("archived", False),
                "fork": repo.get("fork", False),
                "sizeKb": repo.get("size", 0),
            }
        )

    discovered.sort(
        key=lambda item: (item["updatedAt"], item["createdAt"], item.get("pushedAt") or ""),
        reverse=True,
    )
    unresolved = [name for name in config["featuredRepositories"] if normalized_name(name) not in resolved_featured]
    return discovered, unresolved


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


def clipped(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def relative_update(value: str, now: datetime) -> str:
    delta = max(timedelta(0), now - parse_time(value))
    hours = int(delta.total_seconds() // 3600)
    if hours < 1:
        return "UPDATED <1H AGO"
    if hours < 24:
        return f"UPDATED {hours}H AGO"
    days = delta.days
    if days == 1:
        return "UPDATED YESTERDAY"
    if days < 14:
        return f"UPDATED {days}D AGO"
    return f"UPDATED {parse_time(value):%Y-%m-%d}"


def generate_repository_svg(repositories: list[dict], config: dict, now: datetime) -> str:
    recent = [repo for repo in repositories if not (config["excludeFeaturedFromRecent"] and repo["isFeatured"])]
    recent = recent[: int(config["maxRecentRepositories"])]
    if not recent:
        content = "".join(
            [
                text(600, 88, "NO ADDITIONAL PUBLIC REPOSITORIES DETECTED", size=16, anchor="middle", weight=700, spacing=2),
                text(600, 119, "The discovery system will populate this panel on the next six-hour refresh.", size=12, fill=COLORS["muted"], anchor="middle"),
                text(1168, 153, f"TRACKED {len(repositories)} · SYNC {now:%Y-%m-%d %H:%M UTC}", size=9, fill=COLORS["muted"], anchor="end"),
            ]
        )
        return frame("Recent project discovery", "Automatically discovered recent public repositories.", 1200, 170, content)

    rows = (len(recent) + 1) // 2
    height = 72 + rows * 118 + 30
    content = []
    for index, repo in enumerate(recent):
        column = index % 2
        row = index // 2
        x = 28 + column * 586
        y = 56 + row * 118
        width = 558
        state = "NEW REPOSITORY" if repo["isNew"] else relative_update(repo["updatedAt"], now)
        language = repo["primaryLanguage"] or "UNSPECIFIED"
        content.append(f'<rect x="{x}" y="{y}" width="{width}" height="98" rx="5" fill="#090a0c" stroke="#363b43"/>')
        content.append(f'<path d="M{x} {y + 28}V{y}h28M{x + width - 28} {y}h28v28" fill="none" stroke="{COLORS["red_dark"]}" stroke-width="2"/>')
        content.append(text(x + 18, y + 25, clipped(repo["name"], 34), size=15, weight=700, spacing=1))
        content.append(text(x + width - 18, y + 24, state, size=9, fill=COLORS["red"], anchor="end", spacing=1))
        content.append(text(x + 18, y + 51, clipped(repo["description"], 78), size=11, fill=COLORS["silver"]))
        content.append(text(x + 18, y + 76, f"{language.upper()}   ★ {repo['stars']}   ⑂ {repo['forks']}", size=10, fill=COLORS["muted"], spacing=1))
        content.append(text(x + width - 18, y + 76, clipped(repo["url"], 62), size=9, fill=COLORS["muted"], anchor="end"))
    content.append(text(1168, height - 12, f"TRACKED {len(repositories)} · SYNC {now:%Y-%m-%d %H:%M UTC}", size=9, fill=COLORS["muted"], anchor="end"))
    return frame("Recent project discovery", "Automatically discovered recent public repositories sorted by latest update.", 1200, height, "".join(content))


def generate() -> None:
    OUTPUT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    config = load_config()
    profile = request_json(f"{API}/users/{USER}")
    raw_repositories = fetch_repositories()
    repositories, unresolved_featured = build_repository_data(raw_repositories, config, now)

    repository_data = {
        "schemaVersion": 1,
        "generatedAt": now.isoformat(),
        "username": USER,
        "publicRepositoryCount": profile.get("public_repos", len(raw_repositories)),
        "trackedRepositoryCount": len(repositories),
        "unresolvedFeaturedRepositories": unresolved_featured,
        "repositories": repositories,
    }
    REPOSITORIES_PATH.write_text(json.dumps(repository_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUTPUT / "repositories.svg").write_text(generate_repository_svg(repositories, config, now), encoding="utf-8")

    stars = sum(repo["stars"] for repo in repositories)
    stat_items = [
        ("PUBLIC REPOSITORIES", profile.get("public_repos", len(raw_repositories))),
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
    stats_content.append(text(546, 164, f"SYNC {now:%Y-%m-%d UTC}", size=9, fill=COLORS["muted"], anchor="end"))
    (OUTPUT / "stats.svg").write_text(frame("System telemetry", "Current public GitHub account statistics.", 580, 180, "".join(stats_content)), encoding="utf-8")

    language_totals: dict[str, int] = {}
    raw_by_name = {repo["name"].casefold(): repo for repo in raw_repositories}
    for repository in repositories:
        repo = raw_by_name[repository["name"].casefold()]
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
    if not top_languages:
        language_content.append(text(290, 104, "NO LANGUAGE DATA AVAILABLE", size=13, fill=COLORS["muted"], anchor="middle", spacing=1))
    (OUTPUT / "languages.svg").write_text(frame("Language matrix", "Languages aggregated from configured public repositories by GitHub-reported byte count.", 580, 180, "".join(language_content)), encoding="utf-8")

    contribution_content = generate_contributions(now)
    (OUTPUT / "activity.svg").write_text(frame("Contribution activity", "Daily contribution counts for the last year from GitHub's GraphQL API.", 1200, 240, contribution_content), encoding="utf-8")


def generate_contributions(now: datetime) -> str:
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
    labels.append(text(1140, 222, f"LIVE GITHUB DATA · UPDATED {now:%Y-%m-%d UTC}", size=9, fill=COLORS["muted"], anchor="end"))
    return "".join(labels + cells)


if __name__ == "__main__":
    generate()
    print(f"Generated profile metrics and repository discovery data for {USER}")
