#!/usr/bin/env python

import asyncio
from playwright.async_api import async_playwright
import os
import sys
import csv
import json
from datetime import date, timedelta
from urllib.parse import urlparse, parse_qs

download_dir_glob = os.path.abspath("downloads")
report_dir_glob = os.path.abspath("reports")

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

        # Accept cookies
        try:
            await page.wait_for_selector('button#onetrust-accept-btn-handler', timeout=20000)
            await page.click('button#onetrust-accept-btn-handler')
        except:
            pass

        await page.wait_for_timeout(3000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Check for CSV button
        buttons = await page.query_selector_all('button[aria-label="Export table data to CSV"]')
        if not buttons:
            print(f"No CSV available for {outfall_value}")
            await browser.close()
            return None

        # Download CSV
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

        # FIX BOM + quotes in header names
        reader.fieldnames = [h.replace('\ufeff', '').replace('"', '') for h in reader.fieldnames]

        for row in reader:
            # Also clean row keys
            clean_row = {k.replace('\ufeff', '').replace('"', ''): v for k, v in row.items()}
            # print(row)

            record = {
                "Outfall": clean_row.get("Outfall", outfall),
                "Status": clean_row.get("Status"),
                "Start": clean_row.get("Start (Formatted)"),
                "End": clean_row.get("End (Formatted)"),
                "Duration": clean_row.get("Duration"),
                "Bathing Water": clean_row.get("Bathing Water"),
                "Impact Status": clean_row.get("Impact Status")
            }
            records.append(record)

    return records


# ---------------------------------------------------------
# MAIN DATA COLLECTION
# ---------------------------------------------------------
async def get_data(download_dir=download_dir_glob, report_dir=report_dir_glob):

    # Last 3 days
    end_date = date.today()
    # start_date = end_date - timedelta(days=3)
    # For testing
    start_date = end_date - timedelta(days=50)

    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    print(f"Collecting data from {start_str} to {end_str}")

    downloaded_files = []
    all_records = []

    site = "SANDGATE"

    url = f"https://riversandseaswatch.southernwater.co.uk/release-history?BathingSite={site}&StartDate={start_str}T00%3A00&EndDate={end_str}T23%3A59"

    try:
        csv_path = await get_sewage(url, download_dir)
        if csv_path:
            downloaded_files.append(csv_path)
            records = parse_csv_to_records(csv_path)
            all_records.extend(records)
    except Exception as e:
        print(f"Error for {site}: {e}")

    # Write JSON output
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    json_path = os.path.join(report_dir, "sewage.json")

    # If no records, write the "No spills" message
    if len(all_records) == 0:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump({ "message": "No spills", "start_date": start_str, "end_date": end_str }, jf, indent=2)
        print(f"No data found. JSON written to {json_path}")
    else:
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(all_records, jf, indent=2)
        print(f"JSON written to {json_path}")



# ---------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(get_data())
