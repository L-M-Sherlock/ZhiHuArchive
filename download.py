import requests  # type: ignore
import json
from tqdm import tqdm  # type: ignore
from pathlib import Path
import random
import time
import dotenv
import os
from functools import wraps


def retry_with_exponential_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        wait_times = [60 * 2**i for i in range(1, 7)] + [
            64 for _ in range(10)
        ]  # 2min, 4min, 8min, 16min, 32min, 64min
        last_exception = None

        for wait in wait_times:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(e)
                print(f"Attempt failed. Waiting {wait} seconds before retry...")
                last_exception = e
                time.sleep(wait)

        # if all retries failed, raise the last exception
        raise last_exception

    return wrapper


def download_content() -> None:
    dotenv.load_dotenv()
    answer_path = Path("answer")
    answer_path.mkdir(exist_ok=True)

    article_path = Path("article")
    article_path.mkdir(exist_ok=True)

    with open("paths.json", "r", encoding="utf-8") as file:
        paths = json.load(file)

    processed_links = set(answer_path.glob("*.json")) | set(article_path.glob("*.json"))
    processed_ids = set([file.stem for file in processed_links])

    with open("not_found_paths.txt", "r", encoding="utf-8") as file:
        not_found_paths = set(file.read().splitlines())

    paths = list(
        filter(
            lambda x: x not in not_found_paths,
            paths,
        )
    )

    paths = list(
        filter(
            lambda x: x.split("/")[-1] not in processed_ids,
            paths,
        )
    )

    for path in tqdm(paths):
        response = requests.get(os.getenv("API") + path, timeout=10)
        if response.status_code == 403:
            raise Exception(f"Failed to download {path}")
        if response.status_code == 404:
            print(f"Skipping {path} because it does not exist")
            with open("not_found_paths.txt", "a", encoding="utf-8") as file:
                file.write(path + "\n")
            continue
        if "error" in response.json():
            raise Exception(f"Error: {response.json()['error']}")
        type_of_content = "answer" if "answer" in path else "article"
        id_of_content = path.split("/")[-1]
        with open(f"{type_of_content}/{id_of_content}.json", "wb") as file:
            file.write(response.content)

        sleep_time = random.random() * 4 + 1
        time.sleep(sleep_time)


download_content_with_retry = retry_with_exponential_backoff(download_content)
download_content_with_retry()
