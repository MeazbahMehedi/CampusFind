"""Refresh README branding from the single editable developer configuration."""

import json
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
config = json.loads((root / "config/developer.json").read_text(encoding="utf-8"))
for person in config["team"]:
    for field in ("github_url", "linkedin_url", "website"):
        if person.get(field) and urlsplit(person[field]).scheme not in {"http", "https"}:
            raise SystemExit(f"Team {field} must start with http:// or https://")
text = (root / "docs/README.template.md").read_text(encoding="utf-8")
for key, value in config.items():
    if isinstance(value, str):
        text = text.replace("{{" + key + "}}", value)
team = "\n".join(f"| {person['name']} | {person['role']} |" for person in config["team"])
text = text.replace("{{team_table}}", team)
(root / "README.md").write_text(text, encoding="utf-8")
print("README refreshed from config/developer.json. Restart the app for interface changes.")
