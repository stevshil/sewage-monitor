#!/usr/bin/env python

import asyncio
from playwright.async_api import async_playwright
import os
import sys
import csv
import json
from datetime import date, timedelta, datetime
from urllib.parse import urlparse, parse_qs

download_dir_glob = os.path.abspath("downloads")
report_dir_glob = os.path.abspath("reports")

# ---------------------------------------------------------
# Severity ranking
# ---------------------------------------------------------
STATUS_RANK = {
    "Genuine": 3,
    "Potential": 2,
    "Ended": 1,
    "": 0,
    None: 0
}

IMPACT_RANK = {
    "Impacted": 3,
    "Possibly Impacted": 2,
    "Not Impacted": 1,
    "": 0,
    None: 0
}

# ---------------------------------------------------------
# DOWNLOAD CSV FOR ONE SITE
# ---------------------------------------------------------
async def get_sewage(url, download_dir):
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)

        page = await context.new_page()
        await page.goto(url)

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        outfall_value = params.get("Outfall", [None])[0]

        try:
            await page.wait_for_selector('button#onetrust-accept-btn-handler', timeout=20000)
            await page.click('button#onetrust-accept-btn-handler')
        except:
            pass

        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        buttons = await page.query_selector_all('button[aria-label="Export table data to CSV"]')
        if not buttons:
            print(f"No CSV available for {outfall_value}")
            await browser.close()
            return None

        async with page.expect_download() as download_info:
            await page.click('button[aria-label="Export table data to CSV"]')
            await page.click('button[aria-label="Continue"]')

        download = await download_info.value

        filename = f"{outfall_value}.csv"
        final_path = os.path.join(download_dir, filename)
        await download.save_as(final_path)

        await browser.close()
        return final_path


# ---------------------------------------------------------
# PARSE CSV → JSON RECORDS
# ---------------------------------------------------------
def parse_csv_to_records(csv_path):
    records = []
    outfall = os.path.basename(csv_path).replace(".csv", "")

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [h.replace('\ufeff', '').replace('"', '') for h in reader.fieldnames]

        for row in reader:
            clean_row = {k.replace('\ufeff', '').replace('"', ''): v for k, v in row.items()}

            record = {
                "Outfall": clean_row.get("Outfall", outfall),
                "Status": clean_row.get("Status"),
                "Start": clean_row.get("Start (Formatted)"),
                "End": clean_row.get("End (Formatted)"),
                "Duration": clean_row.get("Duration"),
                "BathingWater": clean_row.get("Bathing Water"),
                "ImpactStatus": clean_row.get("Impact Status")
            }
            records.append(record)

    return records


# ---------------------------------------------------------
# CONSOLIDATE SPILLS BY BATHING SITE + DATE
# ---------------------------------------------------------
def consolidate_records(records):
    grouped = {}

    for r in records:
        start_str = r["Start"]
        end_str = r["End"]
        if not start_str or not end_str:
            continue

        dt = datetime.strptime(start_str.split(" ")[0], "%d/%m/%Y")
        date_key = dt.strftime("%Y-%m-%d")

        bw = r["BathingWater"]
        outfall = r["Outfall"]

        key = (bw, date_key)

        if key not in grouped:
            grouped[key] = {
                "Bathing Water": bw,
                "Date": date_key,
                "Earliest Start": r["Start"],
                "Latest End": r["End"],
                "Outfalls": {outfall},
                "Statuses": {r["Status"]},
                "ImpactStatuses": {r["ImpactStatus"]}
            }
        else:
            entry = grouped[key]

            if r["Start"] < entry["Earliest Start"]:
                entry["Earliest Start"] = r["Start"]

            if r["End"] > entry["Latest End"]:
                entry["Latest End"] = r["End"]

            entry["Outfalls"].add(outfall)
            entry["Statuses"].add(r["Status"])
            entry["ImpactStatuses"].add(r["ImpactStatus"])

    # ---------------------------------------------------------
    # ADD TOTAL DURATION + MOST SEVERE STATUS + IMPACT STATUS
    # ---------------------------------------------------------
    final = []

    for entry in grouped.values():
        start_dt = datetime.strptime(entry["Earliest Start"], "%d/%m/%Y %H:%M:%S GMT")
        end_dt = datetime.strptime(entry["Latest End"], "%d/%m/%Y %H:%M:%S GMT")

        duration_seconds = int((end_dt - start_dt).total_seconds())
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        formatted_duration = f"{hours} hours {minutes} minutes"

        # Pick most severe Status
        severe_status = max(entry["Statuses"], key=lambda s: STATUS_RANK.get(s, 0))

        # Pick most severe Impact Status
        severe_impact = max(entry["ImpactStatuses"], key=lambda s: IMPACT_RANK.get(s, 0))

        final.append({
            "BathingWater": entry["Bathing Water"],
            "Date": entry["Date"],
            "Start": entry["Earliest Start"],
            "End": entry["Latest End"],
            "TotalDuration": formatted_duration,
            "AffectedOutfalls": ", ".join(sorted(entry["Outfalls"])),
            "Status": severe_status,
            "ImpactStatus": severe_impact
        })

    return final


# ---------------------------------------------------------
# MAIN DATA COLLECTION
# ---------------------------------------------------------
async def get_data(download_dir=download_dir_glob, report_dir=report_dir_glob):

    pathcontains = os.getenv("PWD", "")
    use_days = 3 if "runner" in pathcontains else 50
    print(f"Delta days = {use_days}")

    end_date = date.today()
    start_date = end_date - timedelta(days=use_days)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    downloaded_files = []
    all_records = []

    site = "SANDGATE"

    url = (
        f"https://riversandseaswatch.southernwater.co.uk/release-history?"
        f"BathingSite={site}&StartDate={start_str}T00%3A00&EndDate={end_str}T23%3A59"
    )

    try:
        csv_path = await get_sewage(url, download_dir)
        if csv_path:
            downloaded_files.append(csv_path)
            records = parse_csv_to_records(csv_path)
            all_records.extend(records)
    except Exception as e:
        print(f"Error for {site}: {e}")

    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    json_path = os.path.join(report_dir, "sewage.json")

    if len(all_records) == 0:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(
                {"message": "No spills", "start_date": start_str, "end_date": end_str},
                jf,
                indent=2
            )
    else:
        consolidated = consolidate_records(all_records)
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(consolidated, jf, indent=2)

    print(f"JSON written to {json_path}")


# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(get_data())
