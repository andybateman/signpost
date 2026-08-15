#!/usr/bin/env python3
"""
Collect Entelar Group vacancies from the Spark NZ careers portal.

The portal (Avature) lists every Spark-family vacancy under one search page and
does not expose a brand filter, so the only reliable way to tell an Entelar
Group role from a Spark NZ one is the "About us" copy in the job description:
Entelar ads open with "At Entelar Group we believe...", Spark ads with
"Spark NZ / As New Zealand's largest telecommunications...".

Job URLs come from the portal's RSS feed rather than the search page -- the
feed is a few KB, the search page is 3.6 MB of inline base64 logos.

Output is jobs.json at the repo root, which is what the boards read. This repo
publishes to GitHub Pages, so writing it here is what makes the careers board
live: a scheduled workflow runs this script and commits the result, and both
the hosted page and the CommBox build fetch that file. Job ads are public, so
unlike the recognition data there is nothing here that should not be published.

    [{"title", "location", "expertise", "level", "employment", "close",
      "ref", "url", "qr"}, ...]

`qr` is the QR module matrix for the job's URL, encoded here by qr.py so the
board can draw it without shipping a QR library to the browser.

Usage:
    python3 scripts/fetch_jobs.py --report        # print what it finds, write nothing
    python3 scripts/fetch_jobs.py                 # write jobs.json
    python3 scripts/fetch_jobs.py --out other.json
"""

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qr  # noqa: E402  -- local module, sits beside this script

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "jobs.json"

PORTAL = "https://careers.sparknz.co.nz/careers"
FEED = PORTAL + "/SearchJobs/feed/?jobRecordsPerPage=500"

# What marks an ad as ours. Both spellings appear in the copy.
BRAND = re.compile(r"entelar\s+group|entelar", re.I)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"

FIELDS = {
    "Location": "location",
    "Expertise": "expertise",
    "Job Level": "level",
    "Employment Type": "employment",
    "Close Date": "close",
    "Ref #": "ref",
}


def get(url, retries=3):
    """Fetch a URL as text, retrying transient failures."""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as res:
                return res.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
    raise SystemExit(f"fetch failed after {retries} attempts: {url}\n  {last}")


def text_of(fragment):
    """Strip tags and collapse whitespace."""
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t).replace("\xa0", " ")).strip()


def job_urls():
    """Every currently advertised job, from the portal's RSS feed."""
    feed = get(FEED)
    seen, urls = set(), []
    for m in re.finditer(r"<link>(https://[^<]*?/JobDetail/[^<]+)</link>", feed):
        url = html.unescape(m.group(1))
        if url not in seen:
            seen.add(url)
            urls.append(url)
    if not urls:
        # An empty feed means the portal changed or is having a bad day, not
        # that Spark stopped hiring. Fail rather than publish an empty board.
        raise SystemExit("feed listed no jobs -- refusing to write an empty list")
    return urls


def parse_job(url):
    """Pull the General information fields and body copy out of a job page."""
    page = get(url)
    # The portal inlines its logos as base64 data URIs -- megabytes of noise
    # that slows every regex below and can false-positive a brand match.
    page = re.sub(r"data:image/[^\"')]+", "", page)

    job = {"url": url}
    for m in re.finditer(
        r'__field__label">(.*?)</div>\s*'
        r'<div class="article__content__view__field__value">(.*?)</div>',
        page, re.S,
    ):
        label, value = text_of(m.group(1)), text_of(m.group(2))
        if label in FIELDS:
            job.setdefault(FIELDS[label], value)

    # The only <h1> on the page is the portal's "Spark Home Page" masthead link;
    # the ad's own title is the og:title meta, with the banner heading as backup.
    title = re.search(r'<meta property="og:title" content="([^"]*)"', page)
    if not title:
        title = re.search(r'class="banner__text__title[^"]*">(.*?)</h2>', page, re.S)
    job["title"] = (
        text_of(title.group(1)) if title
        else url.rstrip("/").split("/")[-2].replace("-", " ")
    )

    # Brand test runs on the visible ad copy only, so a stray "Entelar" in a
    # nav link or tracking blob can't pull a Spark role onto the board.
    body = re.search(r"Description\s*&amp;\s*Requirements(.*)", page, re.S)
    job["_body"] = text_of(body.group(1))[:20000] if body else ""
    return job


def is_entelar(job):
    return bool(BRAND.search(job.get("_body", "")))


def parse_close(value):
    """'21-Aug-2026' -> date. Returns None if absent or unrecognised."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d-%b-%Y").date()
    except ValueError:
        return None


def collect():
    urls = job_urls()
    if not urls:
        raise SystemExit("no jobs in the feed -- the portal may have changed")

    ours, others = [], []
    for url in urls:
        job = parse_job(url)
        (ours if is_entelar(job) else others).append(job)

    today = datetime.now(timezone.utc).date()
    kept = []
    for job in ours:
        close = parse_close(job.get("close"))
        if close and close < today:
            continue  # already closed -- never advertise it on a screen
        kept.append({
            "title": job.get("title", ""),
            "location": job.get("location", ""),
            "expertise": job.get("expertise", ""),
            "level": job.get("level", ""),
            "employment": job.get("employment", ""),
            "close": job.get("close", ""),
            "ref": job.get("ref", ""),
            "url": job["url"],
            # Encoded here rather than in the browser so the board needs no QR
            # library and the standalone stays a single offline file.
            "qr": qr.encode(job["url"]),
        })

    kept.sort(key=lambda j: (parse_close(j["close"]) or today, j["title"]))
    return kept, others


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print the result, write nothing")
    ap.add_argument("--out", type=Path, default=OUTPUT,
                    help="where to write the vacancy file (default: jobs.json)")
    args = ap.parse_args()

    kept, others = collect()

    print(f"{len(kept)} Entelar Group role(s), {len(others)} other Spark-family role(s)")
    for job in kept:
        print(f"  {job['title']}  [{job['location']}]  closes {job['close']}  ref {job['ref']}")
    if args.report:
        for job in others:
            print(f"  (skipped) {job.get('title', '?')}")
        return 0

    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(kept, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
