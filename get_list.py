import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import dotenv
import pandas as pd
import requests

URL_TEMPLATE = "https://www.zhihu.com/api/v4/creators/analysis/realtime/content/list?type={content_type}&format=csv"
DEFAULT_FILENAME = "zhihu_realtime_content.xls"
OUTPUT_DIR = Path("downloads")
ACCOUNTS = (
    {"name": "Thoughts Memo", "slug": "thoughts", "cookie_key": "TM_COOKIE"},
    {"name": "Jarrett Ye", "slug": "jarrett", "cookie_key": "JY_COOKIE"},
)
CONTENT_TYPES = ("article", "answer")


def resolve_filename(content_disposition: Optional[str]) -> str:
    if content_disposition:
        match = re.search(r'filename="?([^";]+)"?', content_disposition)
        if match:
            filename = unquote(match.group(1))
            return Path(filename).name
    return DEFAULT_FILENAME


def normalize_filename(filename: str) -> str:
    try:
        return filename.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return filename


def get_cookie_by_key(cookie_key: str) -> str:
    cookie = dotenv.get_key(".env", cookie_key)
    if not cookie:
        raise RuntimeError(f"{cookie_key} is missing in .env")
    return cookie


def fetch_content(content_type: str, cookie: str) -> requests.Response:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        ),
        "Cookie": cookie,
    }
    response = requests.get(
        URL_TEMPLATE.format(content_type=content_type),
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response


def bytes_to_dataframe(data: bytes) -> pd.DataFrame:
    buffer = BytesIO(data)
    try:
        return pd.read_excel(buffer)
    except ValueError:
        buffer.seek(0)
        return pd.read_csv(buffer)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved CSV to {path}")


def download_for_account(account: dict, content_type: str, date_str: str) -> None:
    cookie = get_cookie_by_key(account["cookie_key"])
    response = fetch_content(content_type, cookie)
    server_filename = normalize_filename(
        resolve_filename(response.headers.get("Content-Disposition"))
    )

    csv_filename = f"{date_str}-{content_type}-{account['slug']}.csv"
    csv_path = OUTPUT_DIR / csv_filename

    df = bytes_to_dataframe(response.content)
    save_csv(df, csv_path)
    print(
        f"Downloaded {account['name']} {content_type} ({server_filename}) as CSV {csv_path}"
    )


def download_all() -> None:
    date_str = datetime.now().strftime("%Y-%m-%d")
    cleanup_old_xls()
    for account in ACCOUNTS:
        for content_type in CONTENT_TYPES:
            download_for_account(account, content_type, date_str)


def cleanup_old_xls() -> None:
    if not OUTPUT_DIR.exists():
        return
    for xls_file in OUTPUT_DIR.glob("*.xls"):
        try:
            xls_file.unlink()
            print(f"Removed leftover XLS {xls_file}")
        except OSError as exc:
            print(f"Failed to remove {xls_file}: {exc}")


if __name__ == "__main__":
    download_all()
