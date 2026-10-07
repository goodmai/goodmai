"""Render assets/radar.svg: a five-axis radar of the last 12 months of GitHub activity.

Needs the `gh` CLI, logged in. Usage: python3 scripts/gen_radar.py
"""
import json, math, subprocess, datetime, pathlib

AI_REPO_OWNERS = {"unslothai", "openvinotoolkit", "mcpjungle", "huggingface", "ml-explore"}
LOGIN = "goodmai"
QUERY = """
query($login:String!){ user(login:$login){ contributionsCollection{
  totalCommitContributions totalIssueContributions
  totalPullRequestContributions totalPullRequestReviewContributions
  pullRequestContributionsByRepository(maxRepositories:100){repository{nameWithOwner} contributions{totalCount}}
  issueContributionsByRepository(maxRepositories:100){repository{nameWithOwner} contributions{totalCount}}
  commitContributionsByRepository(maxRepositories:100){repository{nameWithOwner} contributions{totalCount}}
  pullRequestReviewContributionsByRepository(maxRepositories:100){repository{nameWithOwner} contributions{totalCount}}
}}}"""


def fetch():
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={LOGIN}"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)["data"]["user"]["contributionsCollection"]


def ai_count(c):
    # Contributions to other people's AI / ML infrastructure repos.
    keys = ("pullRequest", "issue", "commit", "pullRequestReview")
    return sum(
        x["contributions"]["totalCount"]
        for k in keys
        for x in c[f"{k}ContributionsByRepository"]
        if x["repository"]["nameWithOwner"].split("/")[0].lower() in AI_REPO_OWNERS
    )


def render(axes):
    cx, cy, r = 260, 235, 140
    n = len(axes)
    peak = max(v for _, v in axes) or 1
    # Square-root scale against the busiest axis, so a small axis stays visible.
    unit = [math.sqrt(v / peak) for _, v in axes]

    def pt(i, k):
        a = -math.pi / 2 + 2 * math.pi * i / n
        return cx + r * k * math.cos(a), cy + r * k * math.sin(a)

    rings = "".join(
        '<polygon points="%s" fill="none" stroke="#00f0ff" stroke-opacity="%.2f"/>'
        % (" ".join("%.1f,%.1f" % pt(i, k) for i in range(n)), 0.12 + 0.05 * k)
        for k in (0.25, 0.5, 0.75, 1.0)
    )
    spokes = "".join(
        '<line x1="%d" y1="%d" x2="%.1f" y2="%.1f" stroke="#00f0ff" stroke-opacity="0.15"/>'
        % ((cx, cy) + pt(i, 1)) for i in range(n)
    )
    poly = " ".join("%.1f,%.1f" % pt(i, u) for i, u in enumerate(unit))
    dots = "".join('<circle cx="%.1f" cy="%.1f" r="4" fill="#00f0ff"/>' % pt(i, u) for i, u in enumerate(unit))
    labels = ""
    for i, (name, v) in enumerate(axes):
        x, y = pt(i, 1.2)
        anchor = "middle" if abs(x - cx) < 10 else ("start" if x > cx else "end")
        labels += (
            '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="14" font-weight="600" fill="#c9d1d9">%s</text>'
            '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="13" fill="#00f0ff">%d</text>'
            % (x, y - 2, anchor, name, x, y + 15, anchor, v)
        )
    today = datetime.date.today().isoformat()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="470" viewBox="0 0 520 470" role="img" aria-label="Contribution radar of goodmai">
  <rect width="520" height="470" rx="12" fill="#0d1117" stroke="#30363d"/>
  <g font-family="'Segoe UI', 'Helvetica Neue', Arial, sans-serif">
    <text x="260" y="34" text-anchor="middle" font-size="18" font-weight="700" fill="#00f0ff">Contribution radar · last 12 months</text>
    {rings}{spokes}
    <polygon points="{poly}" fill="#00f0ff" fill-opacity="0.22" stroke="#00f0ff" stroke-width="2"/>
    {dots}{labels}
    <text x="260" y="452" text-anchor="middle" font-size="11" fill="#8b949e">public activity, √ scale against the busiest axis · AI/ML = work in external AI repos · {today}</text>
  </g>
</svg>
"""


if __name__ == "__main__":
    c = fetch()
    axes = [
        ("Commits", c["totalCommitContributions"]),
        ("Pull requests", c["totalPullRequestContributions"]),
        ("Code review", c["totalPullRequestReviewContributions"]),
        ("Issues", c["totalIssueContributions"]),
        ("AI / ML OSS", ai_count(c)),
    ]
    pathlib.Path(__file__).resolve().parent.parent.joinpath("assets/radar.svg").write_text(render(axes))
    print(axes)
