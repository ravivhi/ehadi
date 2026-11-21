# אחדי - אלופי המספרים

Math adventures for grades 1–6. Installable offline PWA, plus an Android (TWA) wrapper for Google Play as `com.raviv.ehadi`.

Live: https://ravivh.com/ehadi/

## Layout

| Path | What |
|---|---|
| `index.html`, `css/`, `js/`, `icons/`, `manifest.json`, `sw.js`, `privacy.html` | The web app (published) |
| `tests/` | Tests (not published) |
| `android/` | Bubblewrap TWA project that wraps https://ravivh.com/ehadi/ (not published) |

## Publishing the web app

Pushing to `main` does **not** publish anything by itself. When ready, the owner clicks **Run workflow** on [Sync ehadi](https://github.com/ravivhi/guessingGame/actions/workflows/sync-ehadi.yml) in ravivhi/guessingGame, which copies the web files (everything except `tests/`, `android/`, `play-assets/` and repo files) into its `ehadi/` folder, served by GitHub Pages. It's live within a couple of minutes.

**Edit ehadi here, never in guessingGame/ehadi/.** That folder is overwritten on every sync.

Bump the cache version in `sw.js` when changing cached files so installed copies update.

## Building the Android app

Run from **PowerShell** (under Git Bash, `gradlew.bat` is not found):

```powershell
cd android
bubblewrap build
```

Passwords: `~/signing-keys/ehadi/signing-secrets.txt` (keystore and passwords are not in git, so back them up).

- **Do not run `bubblewrap update`.** It regenerates the project from Bubblewrap's template and resets `targetSdkVersion` to 35 and androidbrowserhelper to 2.6.2. Play requires API 36.
- For a new release, bump `versionCode`/`versionName` in `android/app/build.gradle` and `appVersionCode`/`appVersionName` in `android/twa-manifest.json`.
- `.well-known/assetlinks.json` lives at the root of ravivh.com, so in guessingGame, not here.
