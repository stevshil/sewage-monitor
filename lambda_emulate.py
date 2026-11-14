import asyncio
import os
from pathlib import Path

from get_data import get_data

work_dir = Path("./")
download_dir = work_dir / "downloads"
report_dir = work_dir / "reports"

asyncio.run(get_data(str(download_dir), str(report_dir)))

json_path = report_dir / "sewage.json"
if not json_path.is_file():
    raise FileNotFoundError(f"Sewage report was not created: {json_path}")