from pathlib import Path
import random
import time
import requests  # type: ignore
import json
from tqdm import tqdm  # type: ignore
from collections import OrderedDict  # Add this import
from dotenv import load_dotenv
import os

load_dotenv()


def answer_censored_check(url: str) -> bool:
    response = requests.get(url).json()
    if response.get("error"):
        print(url)
        if response["error"]["code"] == 4041:
            return True
        else:
            raise Exception(response["error"])
    return False


def article_censored_check(url: str):
    cookie = os.getenv("COOKIE")
    header = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Cookie": cookie,
    }
    response = requests.get(url, headers=header).json()
    reaction_instruction = response.get("reaction_instruction")
    if reaction_instruction.get("REACTION_GOLDEN_SENTENCE_SHARE"):
        return True
    return False


def load_json_ordered(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.loads(f.read(), object_pairs_hook=OrderedDict)


censorship = load_json_ordered("censorship.json")

# Filter out existing answers and check remaining ones
answer_files = list(
    filter(
        lambda f: f"/answer/{f.stem}" not in censorship,
        Path("answer").glob("*.json"),
    )
)
for file in tqdm(answer_files):
    censorship[f"/answer/{file.stem}"] = answer_censored_check(
        f"https://www.zhihu.com/api/v4/answers/{file.stem}"
    )
    time.sleep(random.random() * 2 + 1)

# Filter out existing articles and check remaining ones
article_files = list(
    filter(lambda f: f"/p/{f.stem}" not in censorship, Path("article").glob("*.json"))
)
for file in tqdm(article_files):
    censorship[f"/p/{file.stem}"] = article_censored_check(
        f"https://www.zhihu.com/api/v4/articles/{file.stem}"
    )
    time.sleep(random.random() * 2 + 1)

with open("censorship.json", "w", encoding="utf-8") as f:
    json.dump(censorship, f, ensure_ascii=False, indent=4)
