import json
import math
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]

end_date = datetime.now(timezone.utc)
start_date = end_date - timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      totalIssueContributions
    }
  }
}
"""

payload = json.dumps(
    {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
        },
    }
).encode("utf-8")

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "github-activity-radar",
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.loads(response.read().decode("utf-8"))

data = result["data"]["user"]["contributionsCollection"]

metrics = {
    "Code Reviews": data["totalPullRequestReviewContributions"],
    "Commits": data["totalCommitContributions"],
    "Pull Requests": data["totalPullRequestContributions"],
    "Issues": data["totalIssueContributions"],
}

total = sum(metrics.values())

if total == 0:
    percentages = {key: 0 for key in metrics}
else:
    percentages = {
        key: round((value / total) * 100, 1)
        for key, value in metrics.items()
    }

width = 760
height = 460
center_x = 380
center_y = 235
radius = 135

axes = [
    ("Code Reviews", -90),
    ("Issues", 0),
    ("Pull Requests", 90),
    ("Commits", 180),
]

def point(angle_degrees: float, scale: float):
    angle = math.radians(angle_degrees)
    x = center_x + radius * scale * math.cos(angle)
    y = center_y + radius * scale * math.sin(angle)
    return round(x, 2), round(y, 2)

grid_levels = [0.25, 0.50, 0.75, 1.00]
grid_lines = []

for level in grid_levels:
    coords = []
    for _, angle in axes:
        x, y = point(angle, level)
        coords.append(f"{x},{y}")
    grid_lines.append(
        f'<polygon points="{" ".join(coords)}" '
        f'fill="none" stroke="#334155" stroke-width="1" opacity="0.55"/>'
    )

axis_lines = []
labels = []
data_points = []

for label, angle in axes:
    x, y = point(angle, 1)
    axis_lines.append(
        f'<line x1="{center_x}" y1="{center_y}" '
        f'x2="{x}" y2="{y}" stroke="#64748b" stroke-width="1.5"/>'
    )

    label_x, label_y = point(angle, 1.28)

    if angle == -90:
        anchor = "middle"
        label_y -= 8
    elif angle == 90:
        anchor = "middle"
        label_y += 20
    elif angle == 0:
        anchor = "start"
        label_x += 12
    else:
        anchor = "end"
        label_x -= 12

    labels.append(
        f'<text x="{label_x}" y="{label_y}" '
        f'fill="#cbd5e1" font-size="16" font-family="Arial, sans-serif" '
        f'text-anchor="{anchor}">{label}</text>'
    )

    scale = percentages[label] / 100
    px, py = point(angle, scale)
    data_points.append(f"{px},{py}")

polygon_points = " ".join(data_points)

value_labels = []

for label, angle in axes:
    scale = percentages[label] / 100
    px, py = point(angle, scale)

    value_x, value_y = point(angle, min(scale + 0.11, 1.12))

    if angle == -90:
        anchor = "middle"
        value_y -= 4
    elif angle == 90:
        anchor = "middle"
        value_y += 12
    elif angle == 0:
        anchor = "start"
        value_x += 8
    else:
        anchor = "end"
        value_x -= 8

    value_labels.append(
        f'<text x="{value_x}" y="{value_y}" '
        f'fill="#f8fafc" font-size="17" font-weight="700" '
        f'font-family="Arial, sans-serif" text-anchor="{anchor}">'
        f'{percentages[label]}%</text>'
    )

raw_values = " • ".join(
    f"{name}: {value}" for name, value in metrics.items()
)

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" rx="18" fill="#0b1620"/>
  <text x="{center_x}" y="42" fill="#f8fafc" font-size="22" font-weight="700"
        font-family="Arial, sans-serif" text-anchor="middle">
    GitHub Activity Breakdown
  </text>
  <text x="{center_x}" y="70" fill="#94a3b8" font-size="14"
        font-family="Arial, sans-serif" text-anchor="middle">
    Public contribution mix — last 365 days
  </text>

  {"".join(grid_lines)}
  {"".join(axis_lines)}

  <polygon points="{polygon_points}" fill="#22c55e" fill-opacity="0.42"
           stroke="#4ade80" stroke-width="3"/>

  {"".join(
      f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="5" fill="#86efac"/>'
      for p in data_points
  )}

  {"".join(labels)}
  {"".join(value_labels)}

  <text x="{center_x}" y="423" fill="#94a3b8" font-size="13"
        font-family="Arial, sans-serif" text-anchor="middle">
    {raw_values}
  </text>
</svg>
"""

output_path = Path("assets/github-activity-radar.svg")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(svg, encoding="utf-8")

print("Generated assets/github-activity-radar.svg")
