# Signpost

EGL office display screens — a quiz board and a live stock price display.

**Keywords:** NZX SPK Spark New Zealand stock price display office screen real-time financial dashboard cake celebration threshold alert GitHub Pages GitHub Actions historical chart NZD market data price tracker EGL Entelar quiz trivia

---

## cake.html — Is There Cake?

Displays **YES** or **NO** based on whether NZX:SPK (Spark New Zealand) is trading at or below $2.00 NZD. Designed as a full-screen office display.

- Coral baseline chart showing 3 months of daily SPK closes
- Green = below $2.00 (cake), red = above $2.00 (no cake)
- Price data updated every 15 minutes via GitHub Actions
- No server required — reads from `raw.githubusercontent.com`

## quiz.html — NZ Trivia Quiz

Full-screen rotating quiz board with 100 New Zealand trivia questions. Cycles automatically between questions and answers.

---

## How it works

`price.json` and `history.json` are written by the scheduled GitHub Actions workflow (`.github/workflows/update-spk.yml`) and committed to the repo. The pages fetch these files from `raw.githubusercontent.com` which serves them with CORS headers, so no backend is needed.

## Usage

Open `cake.html` or `quiz.html` directly in a browser, or deploy to GitHub Pages.
