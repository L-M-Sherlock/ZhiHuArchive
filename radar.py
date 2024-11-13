from pathlib import Path
import random
import time
import requests  # type: ignore
import json
from tqdm import tqdm  # type: ignore
from collections import OrderedDict  # Add this import


def censored_check(url: str) -> bool:
    response = requests.get(url).json()
    if response.get("error"):
        print(url)
        if response["error"]["code"] == 4041:
            return True
        else:
            raise Exception(response["error"])
    return False


def load_json_ordered(file_path):
    with open(file_path, "r") as f:
        return json.loads(f.read(), object_pairs_hook=OrderedDict)


for file in tqdm(list(Path("answer").glob("*.json"))):
    data = load_json_ordered(file)
    if "censored" in data:
        continue
    url = f"https://api.zhihu.com/v4/answers/{file.stem}"
    data["censored"] = censored_check(url)
    with open(file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    time.sleep(random.random() * 2 + 1)


for file in tqdm(list(Path("article").glob("*.json"))):
    data = load_json_ordered(file)
    if "censored" in data:
        continue
    url = f"https://www.zhihu.com/api/v4/articles/{file.stem}"
    data["censored"] = censored_check(url)
    with open(file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    time.sleep(random.random() * 2 + 1)
