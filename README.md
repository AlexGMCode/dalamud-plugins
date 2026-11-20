# Custom FFXIV plugin repository

A [Dalamud](https://github.com/goatcorp/Dalamud) custom plugin repository.
Add the `repo.json` URL once and every plugin listed here shows up in your
in-game plugin installer, auto-updating when a new version is published.

## For players (installing plugins from this repo)

1. In game: `/xlsettings` → **Experimental** → **Custom Plugin Repositories**
2. Add this URL:
   ```
   https://raw.githubusercontent.com/AlexGMCode/dalamud-plugins/main/repo.json
   ```
3. Check **Enabled** → **Save and Close**
4. `/xlplugins` → find a plugin → **Install**

No plugin is installed until you tell it to be — adding the repo only makes
them *available*.

## For the owner (publishing)

```sh
cd ~/Projects/ffxiv/plugin-repo
python3 publish.py --push        # builds all plugins, updates repo.json, commits + pushes
python3 publish.py MyPlugin      # just one
python3 publish_artisan.py --push  # Artisan fork: builds the fork, bumps version (+2), repacks, pushes
```

`publish.py` / `publish_artisan.py` live here with this file. Set `REMOTE`
at the top to the raw base URL of this repo once it's hosted, then
`git push` the `dist/` zips so the download links resolve.

## Plugins

| Plugin | Description |
|---|---|
| ArtisanPrototype | Fork of [PunishXIV/Artisan](https://github.com/PunishXIV/Artisan), renamed so it can coexist with the official Artisan in the same client. Kept current on upstream patches. |
