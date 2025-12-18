import json
from pathlib import Path
from typing import List, Optional

import pandas as pd

DOWNLOADS_DIR = Path("downloads")
ARTICLE_DOMAIN = "https://zhuanlan.zhihu.com"
ANSWER_DOMAIN = "https://www.zhihu.com"


def infer_base_url(csv_path: Path, sample_link: Optional[str]) -> str:
    name = csv_path.name.lower()
    if "-article-" in name:
        return ARTICLE_DOMAIN
    if "-answer-" in name:
        return ANSWER_DOMAIN
    if sample_link:
        if "zhuanlan.zhihu.com" in sample_link:
            return ARTICLE_DOMAIN
        if "www.zhihu.com" in sample_link:
            return ANSWER_DOMAIN
    raise ValueError(f"Cannot determine base URL for {csv_path}")


def load_paths_from_csv(csv_path: Path) -> List[str]:
    df = pd.read_csv(csv_path)
    sample_link = next(
        (link for link in df["链接"] if isinstance(link, str) and link.strip()), None
    )
    base_url = infer_base_url(csv_path, sample_link)
    paths = (
        df["链接"].dropna().astype(str).str.replace(base_url, "", regex=False).to_list()
    )
    print(csv_path.name, len(paths))
    return paths


def load_download_paths(download_dir: Path) -> List[str]:
    if not download_dir.exists():
        print(f"{download_dir} does not exist, skipping download CSVs")
        return []
    all_paths: List[str] = []
    for csv_path in sorted(download_dir.glob("*.csv")):
        all_paths.extend(load_paths_from_csv(csv_path))
    return all_paths


def load_legacy_paths(index_file):
    df = pd.read_csv(index_file, header=None, names=["title", "link", "type"])
    answer_paths = (
        df[df["type"] == "answer"]["link"]
        .str.replace(r"https://www.zhihu.com/question/[0-9]+", "", regex=True)
        .to_list()
    )
    print("old_answer_path", len(answer_paths))

    article_paths = (
        df[df["type"] == "post"]["link"]
        .str.replace("https://zhuanlan.zhihu.com", "", regex=False)
        .to_list()
    )
    print("old_article_path", len(article_paths))
    return answer_paths, article_paths


def sort_key(path):
    # Keep old ordering but guard in case a path does not end with an integer id.
    parts = path.split("/")
    try:
        return parts[-2], int(parts[-1])
    except (IndexError, ValueError):
        return (parts[-2] if len(parts) >= 2 else "", parts[-1] if parts else path)


def main() -> None:
    paths = load_download_paths(DOWNLOADS_DIR)

    old_answer_path, old_article_path = load_legacy_paths("index.csv")
    combined_paths = sorted(
        set(paths + old_answer_path + old_article_path), key=sort_key
    )

    print(len(combined_paths))
    with open("paths.json", "w") as f:
        json.dump(combined_paths, f, indent=4)


if __name__ == "__main__":
    main()
