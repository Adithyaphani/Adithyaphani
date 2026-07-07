import json
import math
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]

NOW = datetime.now(timezone.utc)
START_DATE = NOW - timedelta(days=365)

QUERY = """
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
        "query": QUERY,
        "variables": {
            "login": USERNAME,
            "from": START_DATE.isoformat(),
            "to": NOW.isoformat(),
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

contributions = result["data"]["user"]["contributionsCollection"]

metrics = {
    "Code Reviews": contributions["totalPullRequestReviewContributions"],
    "Commits": contributions["totalCommitContributions"],
    "Pull Requests": contributions["totalPullRequestContributions"],
    "Issues": contributions["totalIssueContributions"],
}

total_activity = sum(metrics.values())

if total_activity == 0:
    percentages = {name: 0.0 for name in metrics}
else:
    percentages = {
        name: round((value / total_activity) * 100, 1)
        for name, value in metrics.items()
    }

WIDTH = 1000
HEIGHT = 560

CENTER_X = 500
CENTER_Y = 275
RADIUS = 150

BACKGROUND = "#0b1620"
GRID_COLOR = "#334155"
AXIS_COLOR = "#64748b"
PRIMARY_TEXT = "#f8fafc"
SECONDARY_TEXT = "#94a3b8"
ACCENT = "#4ade80"
ACCENT_FILL = "#22c55e"


axes = [
    ("Code Reviews", -90),
    ("Issues", 0),
    ("Pull Requests", 90),
    ("Commits", 180),
]


def point(angle_degrees: float, scale: float):
    angle_radians = math.radians(angle_degrees)
    x = CENTER_X + RADIUS * scale * math.cos(angle_radians)
    y = CENTER_Y + RADIUS * scale * math.sin(angle_radians)
    return round(x, 2), round(y, 2)


def svg_text(x, y, text, size=16, color=PRIMARY_TEXT, anchor="middle", weight="400"):
    safe_text = str(text).replace("&", "&amp;")
    return (
        f'<text x="{x}" y="{y}" '
        f'fill="{color}" '
        f'font-size="{size}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="{weight}" '
        f'text-anchor="{anchor}">'
        f"{safe_text}</text>"
    )


grid_polygons = []

for level in [0.25, 0.50, 0.75, 1.0]:
    points = []

    for _, angle in axes:
        x, y = point(angle, level)
        points.append(f"{x},{y}")

    grid_polygons.append(
        f'<polygon points="{" ".join(points)}" '
        f'fill="none" stroke="{GRID_COLOR}" '
        f'stroke-width="1.5" opacity="0.8"/>'
    )

axis_lines = []

for _, angle in axes:
    x, y = point(angle, 1.0)

    axis_lines.append(
        f'<line x1="{CENTER_X}" y1="{CENTER_Y}" '
        f'x2="{x}" y2="{y}" '
        f'stroke="{AXIS_COLOR}" '
        f'stroke-width="1.6"/>'
    )

data_points = []

for label, angle in axes:
    value_scale = percentages[label] / 100
    x, y = point(angle, value_scale)
    data_points.append((label, x, y))

radar_polygon = " ".join(f"{x},{y}" for _, x, y in data_points)

axis_labels = [
    svg_text(CENTER_X, 122, "Code Reviews", size=20, color=SECONDARY_TEXT),
    svg_text(812, CENTER_Y + 8, "Issues", size=20, color=SECONDARY_TEXT),
    svg_text(CENTER_X, 445, "Pull Requests", size=20, color=SECONDARY_TEXT),
    svg_text(188, CENTER_Y + 8, "Commits", size=20, color=SECONDARY_TEXT),
]

percentage_labels = []

for label, angle in axes:
    percentage = percentages[label]

    if angle == -90:
        x, y = CENTER_X, 212
    elif angle == 0:
        x, y = 665, CENTER_Y - 12
    elif angle == 90:
        x, y = CENTER_X, 350
    else:
        x, y = 335, CENTER_Y - 12

    percentage_labels.append(
        svg_text(
            x,
            y,
            f"{percentage}%",
            size=21,
            color=PRIMARY_TEXT,
            weight="700",
        )
    )

metric_cards = [
    ("Code Reviews", metrics["Code Reviews"]),
    ("Commits", metrics["Commits"]),
    ("Pull Requests", metrics["Pull Requests"]),
    ("Issues", metrics["Issues"]),
]

metric_card_width = 205
metric_card_height = 62
metric_card_gap = 18
metric_row_width = (
    len(metric_cards) * metric_card_width
    + (len(metric_cards) - 1) * metric_card_gap
)

metric_start_x = (WIDTH - metric_row_width) / 2
metric_start_y = 476

metric_boxes = []

for index, (label, value) in enumerate(metric_cards):
    x = metric_start_x + index * (metric_card_width + metric_card_gap)

    metric_boxes.append(
        f'<rect x="{x}" y="{metric_start_y}" '
        f'width="{metric_card_width}" height="{metric_card_height}" '
        f'rx="12" fill="#111f2b" stroke="#243447" stroke-width="1"/>'
    )

    metric_boxes.append(
        svg_text(
            x + 16,
            metric_start_y + 24,
            label,
            size=13,
            color=SECONDARY_TEXT,
            anchor="start",
        )
    )

    metric_boxes.append(
        svg_text(
            x + 16,
            metric_start_y + 48,
            value,
            size=20,
            color=PRIMARY_TEXT,
            anchor="start",
            weight="700",
        )
    )

point_circles = []

for _, x, y in data_points:
    point_circles.append(
        f'<circle cx="{x}" cy="{y}" r="6" fill="#86efac" stroke="#dcfce7" stroke-width="1.5"/>'
    )

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="{WIDTH}"
  height="{HEIGHT}"
  viewBox="0 0 {WIDTH} {HEIGHT}">

  <rect width="100%" height="100%" rx="22" fill="{BACKGROUND}"/>

  {svg_text(CENTER_X, 48, "GitHub Activity Breakdown", size=28, color=PRIMARY_TEXT, weight="700")}
  {svg_text(CENTER_X, 78, "Public contribution mix — last 365 days", size=16, color=SECONDARY_TEXT)}

  {"".join(grid_polygons)}
  {"".join(axis_lines)}

  <polygon
    points="{radar_polygon}"
    fill="{ACCENT_FILL}"
    fill-opacity="0.35"
    stroke="{ACCENT}"
    stroke-width="4"
  />

  {"".join(point_circles)}
  {"".join(axis_labels)}
  {"".join(percentage_labels)}
  {"".join(metric_boxes)}

</svg>
"""

output_path = Path("assets/github-activity-radar.svg")
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(svg, encoding="utf-8")

print("Generated assets/github-activity-radar.svg")
print(json.dumps({"metrics": metrics, "percentages": percentages}, indent=2))
