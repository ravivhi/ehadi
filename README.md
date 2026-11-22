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

**Every push to `main` that changes the web app goes live automatically**, within a couple of minutes, on the website and in the Android app. So test before you push. `.github/workflows/publish.yml` asks ravivhi/guessingGame to run [Sync ehadi](https://github.com/ravivhi/guessingGame/actions/workflows/sync-ehadi.yml), which copies the web files (everything except `tests/`, `android/`, `play-assets/`, `tts-proxy/` and repo files) into its `ehadi/` folder, served by GitHub Pages.

To publish again without a code change: Actions → "Publish to ravivh.com/ehadi" → Run workflow.

The only credential here is the secret `GUESSINGGAME_DISPATCH_TOKEN`: a fine-grained token for guessingGame with only "Actions: Read and write" (the same token alfi uses). It can start workflows there but cannot read or change its code. It expires; when publishing fails with an auth error, create a new one and run `gh secret set GUESSINGGAME_DISPATCH_TOKEN -R ravivhi/ehadi` (and the same for ravivhi/alfi).

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
