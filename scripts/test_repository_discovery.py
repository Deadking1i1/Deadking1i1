from datetime import datetime, timezone
import unittest

from scripts.generate_metrics import MISSING_DESCRIPTION, build_repository_data, generate_repository_svg


NOW = datetime(2026, 9, 16, 8, 0, tzinfo=timezone.utc)


def repository(name: str, *, updated: str, created: str = "2026-09-15T08:00:00Z", **overrides) -> dict:
    value = {
        "name": name,
        "full_name": f"Deadking1i1/{name}",
        "html_url": f"https://github.com/Deadking1i1/{name}",
        "description": None,
        "language": "Python",
        "stargazers_count": 2,
        "forks_count": 1,
        "open_issues_count": 0,
        "created_at": created,
        "updated_at": updated,
        "pushed_at": updated,
        "archived": False,
        "fork": False,
        "private": False,
        "size": 12,
    }
    value.update(overrides)
    return value


class RepositoryDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "ignoreRepositories": ["Deadking1i1"],
            "ignorePatterns": ["^scratch-"],
            "featuredRepositories": ["Study-Space"],
            "includeForks": False,
            "includeArchived": False,
            "includeEmpty": True,
            "excludeFeaturedFromRecent": True,
            "maxRecentRepositories": 6,
        }

    def test_filters_sorts_and_preserves_real_metadata(self) -> None:
        fixtures = [
            repository("Deadking1i1", updated="2026-09-16T07:00:00Z"),
            repository("forked", updated="2026-09-16T07:00:00Z", fork=True),
            repository("archived", updated="2026-09-16T07:00:00Z", archived=True),
            repository("scratch-demo", updated="2026-09-16T07:00:00Z"),
            repository("Studyspace", updated="2026-09-16T06:00:00Z", description="Student workspace"),
            repository("Newest", updated="2026-09-16T07:30:00Z"),
            repository("Older", updated="2026-09-12T07:30:00Z", created="2026-08-01T08:00:00Z"),
        ]
        discovered, unresolved = build_repository_data(fixtures, self.config, NOW)

        self.assertEqual([repo["name"] for repo in discovered], ["Newest", "Studyspace", "Older"])
        self.assertTrue(discovered[1]["isFeatured"])
        self.assertEqual(discovered[0]["description"], MISSING_DESCRIPTION)
        self.assertTrue(discovered[0]["isNew"])
        self.assertEqual(unresolved, [])

    def test_recent_svg_excludes_featured_and_contains_real_url(self) -> None:
        fixtures = [
            repository("Studyspace", updated="2026-09-16T06:00:00Z", description="Student workspace"),
            repository("Telemetry", updated="2026-09-16T07:30:00Z", description="Network telemetry tools"),
        ]
        discovered, _ = build_repository_data(fixtures, self.config, NOW)
        svg = generate_repository_svg(discovered, self.config, NOW)

        self.assertIn("Telemetry", svg)
        self.assertIn("https://github.com/Deadking1i1/Telemetry", svg)
        self.assertNotIn("Student workspace", svg)
        self.assertIn("NEW REPOSITORY", svg)


if __name__ == "__main__":
    unittest.main()
