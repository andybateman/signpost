# Announce Screens (signpost)

Screen sources for Entelar Group's Announce Screens — the content set running on the CommBox office boards, plus a few live web boards on GitHub Pages.

**Keywords:** announce screens, digital signage, CommBox, Entelar Group boards, standalone HTML, rewards and recognition, NZ trivia quiz board, careers board, job vacancies, countdown timer, split-flap display, NZX SPK Spark New Zealand stock price, cake threshold alert, GitHub Pages, GitHub Actions, historical chart, NZD market data, price tracker, Jekyll, EGL branding, Spark Wholesale logo, offline capable

---

## The screens

| File | Runs on | What it is |
|------|---------|-----------|
| `rewards-standalone.html` | CommBox | Rewards & Recognition board — deployable artifact, data embedded |
| `rewards.html` | build source | Board template; expects a `rewards.json` (not committed) |
| `quiz-standalone.html` | CommBox | NZ trivia quiz — deployable artifact, logo inlined |
| `quiz.html` | web | NZ trivia quiz, fetching version |
| `jobs-standalone.html` | CommBox | Entelar Group careers board — deployable artifact; reads `jobs.json` live, with a build-time copy as offline fallback |
| `jobs.html` | GitHub Pages + build source | Careers board; reads `jobs.json` from beside it, and is the template the CommBox build is made from |
| `cake.html` | web | Is There Cake? — live SPK price board |
| `worldcup.html` | web | 2026 FIFA World Cup split-flap countdown |
| `countdown.html` | web | Generic countdown, driven by URL params |

## rewards-standalone.html — Rewards & Recognition

Full-screen card board. Shows recipient, team and message on 20-second randomised slides, filtered to recognitions 30–90 days old, with shrink-to-fit for long messages. Names are de-identified to first name + surname initial and nominator sign-offs are stripped. Built by `Scripts/build_standalone.py` in the parent project — do not hand-edit.

## quiz.html — NZ Trivia Quiz

Full-screen rotating quiz board with 100 New Zealand trivia questions. Cycles automatically between questions and answers. Spark Wholesale logo top-left, Entelar Group logo top-right. `quiz-standalone.html` is a self-contained copy for CommBox screens — the logo is embedded as a base64 data URI so it runs offline.

## jobs.html — Entelar Group Careers

Full-screen vacancy board on a deep navy ground. One open Entelar Group role per 15-second slide: the detail on the left — title, location, expertise, job level, employment type, close date and reference — and on the right a white tile holding a QR code that opens that exact job ad, so anyone walking past can apply from their phone. The palette is the same brand set as the recognition board but inverted, navy behind white type with coral accents, because the two screens share a playlist and needed to read as different screens at a glance. The QR tile stays white whatever the board does — inverted codes are unreliable on older phone cameras. Inside the last week before an ad closes the date turns coral and counts down; a role past its close date is never shown, so a screen still running an old upload runs down to the "no roles open right now" card rather than advertising a vacancy that has gone. The board reads its vacancies from `jobs.json` at run time and re-reads it every 30 minutes, so a new role appears on screen without anyone rebuilding or re-uploading. `jobs.json` is kept current by `.github/workflows/update-jobs.yml`, which scrapes the careers portal every 3 hours and commits the result. The CommBox copy fetches the published file by absolute URL, since it has no `jobs.json` beside it once it is inside CommBox, and carries the vacancies as at build time as a fallback for a player that cannot reach the network.

The board cannot read the careers portal directly — the portal sends no CORS headers, so the browser refuses it. That is the whole reason for the scheduled scrape.

`jobs-standalone.html` is built from this template by `Scripts/build_jobs.py` in the parent project — do not hand-edit it.

### scripts/

`fetch_jobs.py` scrapes the careers portal and writes `jobs.json`; `qr.py` encodes the QR codes it embeds; `test_qr.py` proves the encoder still works. They live here rather than in the parent project because this is the repo with Actions behind it — a workflow can only run scripts it can check out. All three are standard library only, so the workflow needs no install step.

## cake.html — Is There Cake?

Displays **YES** or **NO** based on whether NZX:SPK (Spark New Zealand) is trading at or below $2.00 NZD. Designed as a full-screen office display.

- Coral baseline chart showing 3 months of daily SPK closes
- Green = below $2.00 (cake), red = above $2.00 (no cake)
- Price data updated every 15 minutes via GitHub Actions
- No server required — reads from `raw.githubusercontent.com`

## worldcup.html / countdown.html — Countdowns

`worldcup.html` is a split-flap countdown to the 2026 FIFA World Cup. `countdown.html` is the generic version: target date, message and day offset all come from URL params (`?offset=1` for business days + 1).

---

## How it works

`price.json` and `spknz-history.json` are written by the scheduled GitHub Actions workflow (`.github/workflows/update-spk.yml`) and committed to the repo. The web pages fetch these files from `raw.githubusercontent.com`, which serves them with CORS headers, so no backend is needed.

The CommBox screens work the other way: everything is embedded at build time so the player needs no network at all.

## Usage

Open any file directly in a browser, or deploy to GitHub Pages. For CommBox, upload the `-standalone.html` build at https://signage.commbox.com.au/.
