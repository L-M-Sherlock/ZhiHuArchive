import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams


@dataclass(frozen=True)
class SourceConfig:
    key: str
    label: str
    directory: Path
    timestamp_keys: tuple[str, ...]
    unit_label: str


SOURCES: Dict[str, SourceConfig] = {
    "article": SourceConfig(
        key="article",
        label="文章",
        directory=Path("article"),
        timestamp_keys=("created", "updated"),
        unit_label="篇",
    ),
    "answer": SourceConfig(
        key="answer",
        label="回答",
        directory=Path("answer"),
        timestamp_keys=("created_time", "created", "updated_time", "updated"),
        unit_label="条",
    ),
}

CHINESE_FONT_CANDIDATES = [
    "PingFang SC",
    "Heiti SC",
    "STHeiti",
    "Songti SC",
    "SimSun",
    "Microsoft YaHei",
    "SimHei",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
]


class PlainTextExtractor(HTMLParser):
    """HTML parser that converts markup into normalized plain text."""

    BLOCK_TAGS = {
        "p",
        "div",
        "br",
        "li",
        "blockquote",
        "section",
        "article",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self._chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        self._chunks.append(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._chunks.append(unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self._chunks)


def html_to_plain_text(html_content: str) -> str:
    parser = PlainTextExtractor()
    parser.feed(html_content)
    parser.close()
    text = parser.get_text()
    return re.sub(r"\s+", " ", text).strip()


def count_characters(text: str) -> int:
    normalized = re.sub(r"\s+", "", text)
    return len(normalized)


def iter_content_files(directory: Path) -> Iterable[Path]:
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def extract_year(data: dict, timestamp_keys: Iterable[str]) -> Optional[int]:
    for key in timestamp_keys:
        raw_value = data.get(key)
        if raw_value is None or raw_value == "":
            continue
        try:
            timestamp = int(raw_value)
            return datetime.fromtimestamp(timestamp).year
        except (TypeError, ValueError, OSError):
            continue
    return None


def ensure_chinese_font() -> None:
    if getattr(ensure_chinese_font, "_configured", False):
        return

    for font_name in CHINESE_FONT_CANDIDATES:
        try:
            font_manager.findfont(
                font_manager.FontProperties(family=font_name),
                fallback_to_default=False,
            )
        except ValueError:
            continue

        rcParams["font.family"] = font_name
        rcParams["axes.unicode_minus"] = False
        ensure_chinese_font._configured = True
        print(f"使用字体：{font_name}")
        return

    rcParams["axes.unicode_minus"] = False
    ensure_chinese_font._configured = True
    print("警告：未找到中文字体，图表可能无法正确显示中文。")


@dataclass
class StatsResult:
    char_totals: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    count_totals: Dict[int, int] = field(default_factory=lambda: defaultdict(int))


def analyze_source(config: SourceConfig) -> StatsResult:
    result = StatsResult()
    if not config.directory.exists():
        print(f"目录 {config.directory} 不存在，跳过 {config.label}。")
        return result

    for file_path in iter_content_files(config.directory):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"跳过 {file_path}: {exc}")
            continue

        content = data.get("content")
        if not content:
            continue

        year = extract_year(data, config.timestamp_keys)
        if year is None:
            print(f"跳过 {file_path}: 无法确定年份")
            continue

        plain_text = html_to_plain_text(content)
        result.char_totals[year] += count_characters(plain_text)
        result.count_totals[year] += 1

    return result


def print_totals(results: Dict[str, StatsResult], ordered_keys: List[str]) -> None:
    for key in ordered_keys:
        stats = results.get(key)
        if stats is None:
            continue
        char_totals = stats.char_totals
        count_totals = stats.count_totals
        label = SOURCES[key].label
        if not char_totals and not count_totals:
            print(f"{label}: 无数据")
            continue

        print(f"{label}:")
        total_chars = 0
        total_counts = 0
        for year in sorted(set(char_totals) | set(count_totals)):
            char_value = char_totals.get(year, 0)
            count_value = count_totals.get(year, 0)
            total_chars += char_value
            total_counts += count_value
            print(
                f"  {year}: {char_value:,} 字 / {count_value} {SOURCES[key].unit_label}"
            )
        print(f"  合计: {total_chars:,} 字 / {total_counts} {SOURCES[key].unit_label}")


def plot_totals(
    results: Dict[str, StatsResult], ordered_keys: List[str], save_path: Optional[Path]
) -> None:
    ensure_chinese_font()
    years = sorted(
        {year for stats in results.values() for year in stats.char_totals}
    )
    if not years:
        print("没有可视化数据。")
        return

    fig, (ax_char, ax_count) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    x_positions = list(range(len(years)))
    series_count = len(ordered_keys)
    bar_width = 0.8 / max(series_count, 1)

    # Character totals subplot
    for idx, key in enumerate(ordered_keys):
        stats = results.get(key)
        if not stats or not stats.char_totals:
            continue
        offsets = [pos + (idx - (series_count - 1) / 2) * bar_width for pos in x_positions]
        values = [stats.char_totals.get(year, 0) for year in years]
        bars = ax_char.bar(offsets, values, width=bar_width, label=SOURCES[key].label)

        for bar, value in zip(bars, values):
            if value == 0:
                continue
            ax_char.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value / 10_000:.1f} 万字",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax_char.set_ylabel("总字数（纯文本）")
    ax_char.set_title("年度字数统计")
    ax_char.legend()

    # Count totals subplot
    for idx, key in enumerate(ordered_keys):
        stats = results.get(key)
        if not stats or not stats.count_totals:
            continue
        offsets = [pos + (idx - (series_count - 1) / 2) * bar_width for pos in x_positions]
        values = [stats.count_totals.get(year, 0) for year in years]
        bars = ax_count.bar(offsets, values, width=bar_width, label=SOURCES[key].label)

        for bar, value in zip(bars, values):
            if value == 0:
                continue
            ax_count.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax_count.set_xticks(x_positions)
    ax_count.set_xticklabels([str(year) for year in years])
    ax_count.set_xlabel("年份")
    ax_count.set_ylabel("数量")
    ax_count.set_title("年度数量统计")
    ax_count.legend()

    plt.tight_layout()

    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=200)
        print(f"图表已保存到 {save_path}")
    else:
        plt.show()

    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="统计文章与回答的年度字数。")
    parser.add_argument(
        "--types",
        nargs="+",
        choices=sorted(SOURCES.keys()),
        default=list(SOURCES.keys()),
        help="选择要统计的类型（默认：全部）。",
    )
    parser.add_argument(
        "--plot",
        dest="plot",
        action="store_true",
        help="显示可视化图表（默认开启）。",
    )
    parser.add_argument(
        "--no-plot",
        dest="plot",
        action="store_false",
        help="关闭可视化图表。",
    )
    parser.add_argument(
        "--save-plot",
        type=Path,
        default=None,
        help="将图表保存到指定路径（默认不保存，仅展示）。",
    )
    parser.set_defaults(plot=True)
    args = parser.parse_args()

    ordered_keys = [key for key in args.types if key in SOURCES]
    results = {key: analyze_source(SOURCES[key]) for key in ordered_keys}

    print_totals(results, ordered_keys)
    if args.plot:
        plot_totals(results, ordered_keys, args.save_plot)


if __name__ == "__main__":
    main()
