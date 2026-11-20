#!/usr/bin/env python3
"""Publish Dalamud plugins to your custom plugin repository.

Usage:
  python3 publish.py                # build + update repo.json for all plugins in ~/Projects/ffxiv
  python3 publish.py MyPlugin ...   # only named plugin dirs
  python3 publish.py --push         # also git add/commit/push in this repo

Per plugin dir (must contain a .csproj that uses Dalamud.NET.Sdk):
  1. dotnet build <Name>/<Name>.csproj -c Release
  2. copy bin/Release/<Name>/latest.zip -> dist/<Name>/<ver>.zip and dist/<Name>/latest.zip
  3. merge a manifest entry into repo.json (fields from the built <Name>.json)

Before publishing publicly, set REMOTE below to the raw base URL of your
public repo, e.g.:
  REMOTE = "https://raw.githubusercontent.com/<owner>/<repo>/main"
The zips in dist/ must be pushed so those URLs resolve.
"""
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "Projects/ffxiv"
REPO = ROOT / "plugin-repo"
REMOTE = "https://raw.githubusercontent.com/AlexGMCode/dalamud-plugins/main"
SKIP = {"plugin-repo", "SamplePlugin"}


def find_plugins(names):
    out = []
    for d in sorted(ROOT.iterdir()):
        if d.name in SKIP and d.name not in names:
            continue
        if names and d.name not in names:
            continue
        csprojs = [p for p in d.rglob("*.csproj")
                   if "Dalamud.NET.Sdk" in p.read_text(errors="ignore")]
        if csprojs:
            out.append((d, sorted(csprojs)[0]))
    return out


def upsert(entries, entry):
    for i, e in enumerate(entries):
        if e.get("InternalName") == entry.get("InternalName"):
            entries[i] = entry
            return
    entries.append(entry)


def main():
    args = sys.argv[1:]
    names = [a for a in args if not a.startswith("--")]
    push = "--push" in args

    plugins = find_plugins(names)
    if not plugins:
        sys.exit(f"no Dalamud plugins found in {ROOT}")

    repo_json = REPO / "repo.json"
    entries = json.loads(repo_json.read_text()) if repo_json.exists() else []

    for d, csproj in plugins:
        name = d.name
        print(f"== {name}")
        r = subprocess.run(["dotnet", "build", str(csproj), "-c", "Release"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            sys.exit(f"build failed for {name}")

        pdir = csproj.parent
        rel = pdir / "bin" / "Release" / pdir.name
        meta = json.loads((rel / (pdir.name + ".json")).read_text())
        ver = str(meta.get("Version", "0.0.0"))
        ver4 = ver if ver.count(".") == 3 else ver + ".0"
        dl = f"{REMOTE}/dist/{name}/{ver4}.zip" if REMOTE else f"UNHOSTED:dist/{name}/{ver4}.zip"

        entry = {
            "Author": meta.get("Author", ""),
            "Name": meta.get("Name", name),
            "InternalName": meta.get("InternalName", name),
            "Punchline": meta.get("Punchline", ""),
            "Description": meta.get("Description", ""),
            "AssemblyVersion": ver4,
            "RepoUrl": meta.get("RepoUrl", ""),
            "ApplicableVersion": meta.get("ApplicableVersion", "any"),
            "Tags": meta.get("Tags", []),
            "DalamudApiLevel": meta.get("DalamudApiLevel", 15),
            "IconUrl": meta.get("IconUrl", ""),
            "DownloadLinkInstall": dl,
            "DownloadLinkUpdate": dl,
            "DownloadLinkTesting": dl,
            "Changelog": meta.get("Changelog", f"{ver4} — published {datetime.now(timezone.utc):%Y-%m-%d}"),
            "IsHide": False,
            "IsTestingExclusive": False,
        }

        dist = REPO / "dist" / name
        dist.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rel / "latest.zip", dist / f"{ver4}.zip")
        shutil.copy2(rel / "latest.zip", dist / "latest.zip")
        upsert(entries, entry)
        print(f"   {ver4} -> dist/{name}/, entry upserted")

    repo_json.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"repo.json now lists {len(entries)} plugin(s)")

    if push:
        for cmd in (["git", "add", "-A"],
                    ["git", "commit", "-m",
                     "publish " + (", ".join(names) or "all") +
                     " @" + datetime.now().isoformat(timespec="seconds")],
                    ["git", "push"]):
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr)
                sys.exit(f"git step failed: {cmd}")
        print("pushed")


if __name__ == "__main__":
    main()
