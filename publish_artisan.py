#!/usr/bin/env python3
"""Build & publish the Artisan fork (~/Projects/ffxiv/Artisan) to the custom repo.

Artisan is a hand-written csproj (not Dalamud.NET.Sdk), so it needs:
  * -p:DalamudLibPath  -> local Dalamud dev DLLs ($(appdata) is empty on Linux)
  * -p:EnableWindowsTargeting -> net10.0-windows TFM on Linux
  * -p:Version         -> fork version = upstream csproj <Version> with last
    component +2 (puni.sh deploys csproj+1; +2 keeps us clear of their line)
  * zip post-processing: rename Artisan.json -> plugin.json (Dalamud installs
    require plugin.json; the upstream host injects it at delivery instead)
    and repoint RepoUrl/DownloadLink* at this repo.

Usage:
  python3 publish_artisan.py            # build + stage dist + update repo.json
  python3 publish_artisan.py --push     # also git add/commit/push
  python3 publish_artisan.py --version 4.0.5.30   # override version

Only dist/Artisan/latest.zip is committed (the versioned name would double
the ~11MB per publish); repo.json links point at it.
"""
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / "Projects/ffxiv"
REPO = ROOT / "plugin-repo"
ARTISAN = ROOT / "Artisan"
CSPROJ = ARTISAN / "Artisan" / "Artisan.csproj"
ZIP_IN = ARTISAN / "Artisan" / "bin" / "Release" / "Artisan" / "latest.zip"
DALAMUD_DEV = Path.home() / ".xlcore" / "dalamud" / "Hooks" / "dev"
REMOTE = "https://raw.githubusercontent.com/AlexGMCode/dalamud-plugins/main"
FORK_URL = "https://github.com/AlexGMCode/Artisan"


def csproj_version() -> str:
    m = re.search(r"<Version>([\d.]+)</Version>", CSPROJ.read_text())
    assert m, "no <Version> in Artisan.csproj"
    parts = m.group(1).split(".")
    return ".".join(parts[:-1] + [str(int(parts[-1]) + 2)])


def postprocess_zip(src: Path, dst: Path, ver: str):
    dl = f"{REMOTE}/dist/Artisan/latest.zip"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename == "Artisan.json":
                meta = json.loads(zin.read(info))
                meta["AssemblyVersion"] = ver
                meta["RepoUrl"] = FORK_URL
                meta["DownloadLinkInstall"] = dl
                meta["DownloadLinkUpdate"] = dl
                meta.pop("DownloadLinkTesting", None)
                data = json.dumps(meta, indent=2).encode()
                name = "plugin.json"
            else:
                data = zin.read(info)
                name = info.filename
            zout.writestr(name, data)


def upsert(entries, entry):
    for i, e in enumerate(entries):
        if e.get("InternalName") == entry.get("InternalName"):
            entries[i] = entry
            return
    entries.append(entry)


def main():
    args = sys.argv[1:]
    push = "--push" in args
    ver_override = None
    if "--version" in args:
        ver_override = args[args.index("--version") + 1]
    ver = ver_override or csproj_version()
    print(f"== Artisan {ver}")

    r = subprocess.run(
        ["dotnet", "build", str(CSPROJ), "-c", "Release",
         f"-p:DalamudLibPath={DALAMUD_DEV}/",
         "-p:EnableWindowsTargeting=true",
         f"-p:Version={ver}"],
        cwd=ARTISAN, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        sys.exit("build failed")

    if not ZIP_IN.exists():
        sys.exit(f"packager zip not found at {ZIP_IN}")
    meta = json.loads(zipfile.ZipFile(ZIP_IN).read("Artisan.json"))
    if str(meta.get("AssemblyVersion")) != ver:
        print(f"   note: zip manifest version {meta.get('AssemblyVersion')} != requested {ver}")

    dist = REPO / "dist" / "Artisan"
    dist.mkdir(parents=True, exist_ok=True)
    postprocess_zip(ZIP_IN, dist / "latest.zip", ver)
    print(f"   {dist / 'latest.zip'} ({(dist / 'latest.zip').stat().st_size // 1024} KB)")

    repo_json = REPO / "repo.json"
    entries = json.loads(repo_json.read_text()) if repo_json.exists() else []
    entry = {
        "Author": meta.get("Author", ""),
        "Name": meta.get("Name", "Artisan"),
        "InternalName": "Artisan",
        "Punchline": meta.get("Punchline", ""),
        "Description": meta.get("Description", ""),
        "AssemblyVersion": ver,
        "RepoUrl": FORK_URL,
        "ApplicableVersion": meta.get("ApplicableVersion", "any"),
        "Tags": meta.get("Tags", ["crafting"]),
        "DalamudApiLevel": meta.get("DalamudApiLevel", 15),
        "IconUrl": meta.get("IconUrl", ""),
        "DownloadLinkInstall": f"{REMOTE}/dist/Artisan/latest.zip",
        "DownloadLinkUpdate": f"{REMOTE}/dist/Artisan/latest.zip",
        "Changelog": meta.get("Changelog", f"{ver} — fork published {datetime.now(timezone.utc):%Y-%m-%d}"),
        "IsHide": False,
        "IsTestingExclusive": False,
    }
    upsert(entries, entry)
    repo_json.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"repo.json now lists {len(entries)} plugin(s)")

    if push:
        for cmd in (["git", "add", "-A"],
                    ["git", "commit", "-m", f"publish Artisan {ver} @ {datetime.now().isoformat(timespec='seconds')}"],
                    ["git", "push"]):
            r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr)
                sys.exit(f"git step failed: {cmd}")
        print("pushed")


if __name__ == "__main__":
    main()
