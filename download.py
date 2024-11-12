import requests  # type: ignore
import json
from tqdm import tqdm  # type: ignore
from pathlib import Path
import random
import time
import dotenv
import os


dotenv.load_dotenv()
answer_path = Path("answer")
answer_path.mkdir(exist_ok=True)

article_path = Path("article")
article_path.mkdir(exist_ok=True)

with open("paths.json", "r") as file:
    paths = json.load(file)

processed_links = set(answer_path.glob("*.json")) | set(article_path.glob("*.json"))
processed_ids = [file.stem for file in processed_links]

paths = list(filter(lambda x: x.split("/")[-1] not in processed_ids, paths))

for path in tqdm(paths):
    response = requests.get(os.getenv("API") + path)
    type_of_content = "answer" if "answer" in path else "article"
    id_of_content = path.split("/")[-1]
    with open(f"{type_of_content}/{id_of_content}.json", "wb") as file:
        file.write(response.content)

    sleep_time = random.randint(1, 5)
    time.sleep(sleep_time)
