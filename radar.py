import argparse
from pathlib import Path
import random
import time
import requests  # type: ignore
import json
from tqdm import tqdm  # type: ignore
from collections import OrderedDict
from dotenv import load_dotenv
import os

load_dotenv()
_CENSORSHIP_PATH = Path("censorship.json")
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
AUTHOR_COOKIE_KEYS = {
    "Thoughts Memo": "COOKIE_B",
    "Jarrett Ye": "COOKIE_A",
}


def cookie_key_for_author(data: dict) -> str:
    author_name = (data.get("author") or {}).get("name")
    cookie_key = AUTHOR_COOKIE_KEYS.get(author_name)
    if not cookie_key:
        raise RuntimeError(f"Cannot determine cookie for author: {author_name}")
    return cookie_key


def _fetch_with_cookie(url: str, cookie_key: str) -> dict:
    cookie = os.getenv(cookie_key)
    if not cookie:
        raise RuntimeError(f"{cookie_key} is missing in .env")
    headers = {"User-Agent": _USER_AGENT, "Cookie": cookie}
    response = requests.get(url, headers=headers, timeout=30).json()
    error = response.get("error")
    if error and error.get("code") == 10003:
        raise RuntimeError(f"{cookie_key} is invalid: {error}")
    return response


def answer_censored_check(url: str, cookie_key: str) -> bool:
    response = _fetch_with_cookie(url, cookie_key)
    if response.get("error"):
        print(url)
        if response["error"]["code"] == 4041:
            return True
        raise Exception(response["error"])
    return False


def article_censored_check(url: str, cookie_key: str) -> bool:
    response = _fetch_with_cookie(url, cookie_key)
    if response.get("error"):
        print(url)
        if response["error"]["code"] == 4041:
            return True
        raise Exception(response["error"])
    reaction_instruction = response.get("reaction_instruction") or {}
    if reaction_instruction.get("REACTION_GOLDEN_SENTENCE_SHARE"):
        return True
    return False


def load_json_ordered(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.loads(f.read(), object_pairs_hook=OrderedDict)


def save_censorship(payload: OrderedDict) -> None:
    """Persist progress after each check so interrupted runs keep their state."""
    tmp_path = _CENSORSHIP_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)
        f.write("\n")
    tmp_path.replace(_CENSORSHIP_PATH)


def sleep_between_requests(sleep_min: float, sleep_max: float) -> None:
    if sleep_max <= 0:
        return
    time.sleep(random.uniform(sleep_min, sleep_max))


def answer_files_to_check(censorship: OrderedDict, refresh_all: bool) -> list[Path]:
    files = sorted(Path("answer").glob("*.json"))
    if refresh_all:
        return files
    return [file for file in files if f"/answer/{file.stem}" not in censorship]


def article_files_to_check(censorship: OrderedDict, refresh_all: bool) -> list[Path]:
    files = sorted(Path("article").glob("*.json"))
    if refresh_all:
        return files
    return [file for file in files if f"/p/{file.stem}" not in censorship]


def check_answer(file: Path, censorship: OrderedDict) -> None:
    data = load_json_ordered(file)
    cookie_key = cookie_key_for_author(data)
    censorship[f"/answer/{file.stem}"] = answer_censored_check(
        f"https://www.zhihu.com/api/v4/answers/{file.stem}",
        cookie_key,
    )


def check_article(file: Path, censorship: OrderedDict) -> None:
    data = load_json_ordered(file)
    cookie_key = cookie_key_for_author(data)
    censorship[f"/p/{file.stem}"] = article_censored_check(
        f"https://www.zhihu.com/api/v4/articles/{file.stem}",
        cookie_key,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查知乎归档内容是否被屏蔽。")
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="重新检查所有本地 article/answer JSON，而不只是 censorship.json 中缺失的条目。",
    )
    parser.add_argument(
        "--content",
        choices=("all", "answers", "articles"),
        default="all",
        help="要检查的内容类型（默认：all）。",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=0,
        help="从排序后的文件列表第几个开始检查，用于恢复中断任务；0 表示从头开始。",
    )
    parser.add_argument(
        "--sleep-min",
        type=float,
        default=1,
        help="请求之间的最短等待秒数（默认：1）。",
    )
    parser.add_argument(
        "--sleep-max",
        type=float,
        default=3,
        help="请求之间的最长等待秒数（默认：3）。设为 0 可关闭等待。",
    )
    args = parser.parse_args()
    if args.sleep_min < 0 or args.sleep_max < 0:
        parser.error("--sleep-min and --sleep-max must be non-negative")
    if args.sleep_max and args.sleep_min > args.sleep_max:
        parser.error("--sleep-min must not exceed --sleep-max")
    if args.start_index < 0:
        parser.error("--start-index must be non-negative")
    return args


def main() -> None:
    args = parse_args()
    censorship = load_json_ordered("censorship.json")

    if args.content in ("all", "answers"):
        answer_files = answer_files_to_check(censorship, args.refresh_all)
        if args.start_index:
            answer_files = answer_files[args.start_index :]
        print(f"Checking {len(answer_files)} answers")
        for file in tqdm(answer_files):
            check_answer(file, censorship)
            save_censorship(censorship)
            sleep_between_requests(args.sleep_min, args.sleep_max)

    if args.content in ("all", "articles"):
        article_files = article_files_to_check(censorship, args.refresh_all)
        if args.start_index:
            article_files = article_files[args.start_index :]
        print(f"Checking {len(article_files)} articles")
        for file in tqdm(article_files):
            check_article(file, censorship)
            save_censorship(censorship)
            sleep_between_requests(args.sleep_min, args.sleep_max)

    save_censorship(censorship)


if __name__ == "__main__":
    main()
