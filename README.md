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

**Every push to `main` that changes the web app goes live automatically**, within a couple of minutes, on the website and in the Android app. So test before you push. `.github/workflows/pages.yml` publishes the web files (everything except `tests/`, `android/`, `play-assets/`, `tts-proxy/` and repo files) with this repo's GitHub Pages. ravivh.com is the custom domain of [ravivhi/ravivhi.github.io](https://github.com/ravivhi/ravivhi.github.io), so this repo's own GitHub Pages site is served at ravivh.com/ehadi/. No other repo is involved and no token is needed.

To publish again without a code change: Actions → "Publish to ravivh.com/ehadi (Pages)" → Run workflow.

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
- `.well-known/assetlinks.json` lives at the root of ravivh.com, so in ravivhi/ravivhi.github.io, not here.
