#!/usr/bin/env python3
import subprocess
import csv
from collections import Counter
from pathlib import Path

# ---------- CONFIG ----------
TOP_N = 50
EXCLUDE_DIRS = {".git", "node_modules", "dist", "build", "target", ".venv", "venv", ".next"}
ONLY_EXTS = {".py"}  # change to match your language
SONAR_CSV = "sonarqube_issues.csv"  # expected columns: file,issues
OUTPUT_HTML = "file_change_histogram.html"
OUTPUT_CSV = "file_change_counts.csv"
TITLE = "File change frequency vs SonarQube issues"

# ---------- DATA COLLECTION ----------
def get_change_counts():
    res = subprocess.run(
        ["git", "log", "--name-only", "--diff-filter=AMR", "--pretty=format:"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
    )
    if res.returncode != 0:
        raise RuntimeError(res.stderr.strip())

    files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    counts = Counter()
    for f in files:
        p = Path(f)
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if ONLY_EXTS and p.suffix not in ONLY_EXTS:
            continue
        counts[f] += 1
    return counts


def read_sonar_issues(path):
    issues = {}
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                file = row["file"].strip()
                issues[file] = int(row.get("issues", 0))
    except FileNotFoundError:
        print(f"⚠️ SonarQube CSV not found: {path}")
    return issues


# ---------- MAIN ----------
def main():
    try:
        counts = get_change_counts()
    except Exception as e:
        print("❌", e)
        return

    if not counts:
        print("No matching file changes found. Check extension filter or repo path.")
        return

    sonar_issues = read_sonar_issues(SONAR_CSV)

    # merge and sort
    merged = []
    for file, count in counts.items():
        merged.append((file, count, sonar_issues.get(file, 0)))  # (file, commits, issues)

    merged.sort(key=lambda x: (-x[1], x[0]))  # sort by change count desc
    if TOP_N:
        merged = merged[:TOP_N]

    # export CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "change_count", "issues"])
        w.writerows(merged)

    # plotting
    import pandas as pd
    import plotly.express as px

    df = pd.DataFrame(merged, columns=["file", "change_count", "issues"])
    df["rank"] = range(len(df))

    # color scale from green (0 issues) to red (max issues)
    fig = px.bar(
        df,
        x="rank",
        y="change_count",
        color="issues",
        color_continuous_scale="RdYlGn_r",  # reversed so red = many issues
        hover_data={"file": True, "change_count": True, "issues": True, "rank": False},
        title=f"{TITLE} (top {len(df)})",
    )

    fig.update_layout(
        xaxis=dict(showticklabels=False, title=""),
        yaxis_title="Commits touching file",
        coloraxis_colorbar_title="Issues",
        template="plotly_white",
        height=520,
        margin=dict(l=40, r=20, t=60, b=40),
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Commits: %{y}<br>Issues: %{customdata[1]}<extra></extra>",
        customdata=df[["file", "issues"]],
    )

    fig.write_html(OUTPUT_HTML, include_plotlyjs="inline", full_html=True, auto_open=True)
    print(f"✅ Wrote {OUTPUT_CSV}")
    print(f"✅ Wrote {OUTPUT_HTML} (open in browser or embed via <iframe>)")


if __name__ == "__main__":
    main()
