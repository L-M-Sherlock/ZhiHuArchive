import json
import re
from pathlib import Path
from datetime import datetime
from html import escape
from tqdm import tqdm
from feedgen.feed import FeedGenerator
import zoneinfo
from bs4 import BeautifulSoup


BASE_URL = "https://l-m-sherlock.github.io/ZhiHuArchive"

article_ids = [file.stem for file in Path("./article").glob("*.json")]
answer_ids = [file.stem for file in Path("./answer").glob("*.json")]

fg = FeedGenerator()
fg.id(f"{BASE_URL}/feed.xml")
fg.title("Thoughts Memo")
fg.link(href=f"{BASE_URL}/", rel="self")
fg.description("知乎账号 @Thoughts Memo 和 @Jarrett Ye 的文章和回答的存档")
fg.language("zh-Hans")
fg.generator("feedgen", uri="https://github.com/lkiesow/python-feedgen")
fg.icon(f"{BASE_URL}/favicon.ico")
fg.logo(f"{BASE_URL}/favicon.ico")


def archive_url(stem: str) -> str:
    return f"{BASE_URL}/{stem}.html"


def source_url(data: dict, stem: str) -> str:
    if "question" in data:
        return f"https://www.zhihu.com/question/{data['question']['id']}/answer/{stem}"
    return f"https://zhuanlan.zhihu.com/p/{stem}"


def add_item(data, full_html):
    created_timestamp = datetime.fromtimestamp(
        data["created"] if "created" in data else data["created_time"],
        zoneinfo.ZoneInfo("Asia/Shanghai"),
    )
    title = data["question"]["title"] if "question" in data else data["title"]
    fe = fg.add_entry()
    fe.title(title)
    fe.link(href=archive_url(file.stem), rel="alternate")
    fe.link(href=source_url(data, file.stem), rel="related")
    fe.content(full_html, type="html")
    fe.summary(strip_html_tags(data.get("excerpt", "")))
    fe.published(created_timestamp)
    fe.guid(archive_url(file.stem))


def replace_url(url: str) -> str:
    _id = url.split("/")[-1]
    if _id in article_ids or _id in answer_ids:
        return f"./{_id}.html"
    return url


def process_content(content: str) -> str:
    # Parse HTML content
    soup = BeautifulSoup(content, "html.parser")

    # Process img tags
    for img in soup.find_all("img"):
        actualsrc = img.get("data-actualsrc")
        if actualsrc:
            img["src"] = actualsrc
            del img["data-actualsrc"]

    # Process anchor tags
    for a in soup.find_all("a"):
        href = a.get("href")
        if href and href.startswith("https://link.zhihu.com/"):
            try:
                # Convert relative URL to absolute
                full_url = "https:" + href if href.startswith("//") else href
                from urllib.parse import urlparse, parse_qs

                parsed = urlparse(full_url)
                target = parse_qs(parsed.query).get("target", [None])[0]
                if target:
                    decoded_target = target.replace("https%3A", "https:").replace(
                        "http%3A", "http:"
                    )
                    a["href"] = replace_url(decoded_target)
            except Exception as e:
                print(f"Failed to parse URL {href}: {e}")
                continue
        elif href:
            a["href"] = replace_url(href)

        # Ensure links open in a new tab safely.
        rel_attr = a.get("rel", [])
        rel_values = rel_attr.split() if isinstance(rel_attr, str) else list(rel_attr)
        for value in ("noopener", "noreferrer"):
            if value not in rel_values:
                rel_values.append(value)
        if rel_values:
            a["rel"] = rel_values
        a["target"] = "_blank"

    # Remove u tags but keep their contents
    for u in soup.find_all("u"):
        u.unwrap()

    return str(soup)


def strip_html_tags(value: str) -> str:
    return clean_text(value)


def clean_text(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def truncate_text(value: str, max_length: int = 160) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip(" ,.;，。；、") + "..."


def build_meta_description(primary: str, *fallbacks: str) -> str:
    parts = []
    for value in (primary, *fallbacks):
        text = clean_text(value)
        if text and text not in parts:
            parts.append(text)

    description = parts[0] if parts else ""
    if len(description) < 80:
        for text in parts[1:]:
            if text not in description:
                description = f"{description} {text}".strip()
            if len(description) >= 80:
                break

    if not description:
        description = "知乎账号 @Thoughts Memo 和 @Jarrett Ye 的文章和回答存档"
    return truncate_text(description)


def html_attr(value: str) -> str:
    return escape(str(value or ""), quote=True)


def schema_datetime(timestamp: int) -> str:
    return datetime.fromtimestamp(
        timestamp,
        zoneinfo.ZoneInfo("Asia/Shanghai"),
    ).isoformat()


def article_schema(
    *,
    title: str,
    description: str,
    archive_url_value: str,
    author_name: str,
    author_url_value: str,
    published_timestamp: int,
    modified_timestamp: int,
    image_url: str = "",
) -> dict:
    author = {"@type": "Person", "name": author_name}
    if author_url_value:
        author["url"] = author_url_value

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "author": author,
        "datePublished": schema_datetime(published_timestamp),
        "dateModified": schema_datetime(modified_timestamp),
        "mainEntityOfPage": {"@type": "WebPage", "@id": archive_url_value},
        "url": archive_url_value,
        "isPartOf": {
            "@type": "WebSite",
            "name": "ZhiHu Archive for Thoughts Memo",
            "url": f"{BASE_URL}/",
        },
    }
    if image_url:
        schema["image"] = [image_url]
    return schema


def json_ld_script(schema: dict) -> str:
    content = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return f'<script type="application/ld+json">{content}</script>'


def normalize_author_url(url: str) -> str:
    if not url:
        return ""
    prefix_map = {
        "https://api.zhihu.com/people/": "https://www.zhihu.com/people/",
        "https://www.zhihu.com/api/v4/people/": "https://www.zhihu.com/people/",
        "https://www.zhihu.com/people/": "https://www.zhihu.com/people/",
    }
    for prefix, replacement in prefix_map.items():
        if url.startswith(prefix):
            suffix = url[len(prefix) :]
            return replacement + suffix
    if url.startswith("/people/"):
        return f"https://www.zhihu.com{url}"
    return url


def extract_reference(html: str) -> str:
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    references = {}

    # Find all sup elements and collect references
    for sup in soup.find_all("sup"):
        text = sup.get("data-text")
        url = sup.get("data-url")
        numero = sup.get("data-numero")

        if text and url and numero:
            references[numero] = {"text": text, "url": replace_url(url)}

    # Generate reference list if any references were found
    if references:
        reference_list = [
            f'{index}. {ref["text"]} <a href="{ref["url"]}" target="_blank" rel="noopener noreferrer">{ref["url"]}</a>'
            for index, ref in sorted(references.items(), key=lambda item: int(item[0]))
        ]
        return f'<hr><section data-pagefind-ignore><h2>参考</h2>{"<br>".join(reference_list)}</section>'

    return ""


# Create HTML template
article_template = """<!DOCTYPE html>
<html lang="zh">
<head>
    <title>${"title"} | ZhiHu Archive</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} | ZhiHu Archive">
    <meta property="og:site_name" content="ZhiHu Archive for Thoughts Memo">
    <meta property="og:url" content="${"archive_url"}">
    <meta property="og:image" content="${"image_url"}">
    <meta property="og:description" content="${"meta_description"}">
    <meta name="description" content="${"meta_description"}">
    <meta data-pagefind-meta="title" content="${"title"}">
    <meta data-pagefind-meta="image" content="${"image_url"}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="${"title"} | ZhiHu Archive">
    <meta name="twitter:description" content="${"meta_description"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <meta name="google-site-verification" content="U7ZAFUgGNK60mmMqaRygg5vy-k8pwbPbDFXNjDCu7Xk" />
    <link rel="canonical" href="${"archive_url"}">
    <link rel="alternate" type="application/rss+xml" title="ZhiHu Archive for Thoughts Memo" href="https://l-m-sherlock.github.io/ZhiHuArchive/feed.xml">
    <link rel="stylesheet" href="https://gcore.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    ${"json_ld"}
    <script>
        const redirect = ${"redirect"};
        if (redirect) {
            window.location.replace("${"source_url"}");
        }
    </script>
    <style>
        .origin_image {
            width: 100%;
        }
        figure {
            margin: 1.4em 0;
        }
        figure img {
            width: 100%;
        }
        img {
            vertical-align: middle;
        }
        .author {
            display: flex;
            gap: 1em;
            align-items: center;
        }
        #avatar {
            width: 100px;
            height: 100px;
        }
        .author > div {
            flex: 1;
        }
        a {
            color: #2563eb;
            text-decoration: none;
            border-bottom: 1px solid rgba(37, 99, 235, 0.3);
            border-radius: 4px;
            padding: 0 0.1em;
            transition: color 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
        }
        a:hover,
        a:focus-visible {
            color: #1d4ed8;
            border-bottom-color: rgba(29, 78, 216, 0.6);
            background-color: rgba(37, 99, 235, 0.08);
        }
        a:focus-visible {
            outline: none;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
        }
        a[data-draft-type="link-card"] {
            display: block;
            border-bottom: none;
            padding: 0;
            background: none;
        }
        .references {
            font-size: 0.85em;
        }
        .formula-display {
            display: block;
            text-align: center;
        }
    </style>
</head>
<body style="max-width: 1000px; margin: 0 auto; padding: 0 1em 0 1em;" class="yue">
    <p data-pagefind-ignore><a href="./">← 返回目录</a></p>
    <hr>
    <header>
        <img class="origin_image" src="${"image_url"}"/>
        <h1><a href="${"source_url"}" target="_blank" rel="noopener noreferrer">${"title"}</a></h1>
        <div class="author">
            <img class="avatar" id="avatar" src="${"avatar_url"}" />
            <div>
                <h2 rel="author">
                    <a href="${"author_url"}" target="_blank" rel="noopener noreferrer">@${"author"}</a>
                </h2>
                <p>${"headline"}</p>
            </div>
        </div>
        <time datetime="${"created_time"}">发表于 ${"created_time_formatted"}</time>
        <p rel="stats"style="color: #999; font-size: 0.9em;">${"voteup_count"} 👍 / ${"comment_count"} 💬</p>
    </header>
    <article data-pagefind-body>
        ${"content"}
        ${"reference"}
        <hr>
        <div class="column" style="margin: 1em 0; padding: 0.5em 1em; border: 2px solid #999; border-radius: 5px;" data-pagefind-ignore>
            <h2>专栏：${"column_title"}</h2>
            <p>${"column_description"}</p>
        </div>
        <hr>
        <p data-pagefind-ignore><a href="./">← 返回目录</a></p>
    </article>
    <footer>
        <p style="color: #999; font-size: 0.85em; text-align: center; margin-top: 2em;">
            本页面由 <a href="https://github.com/L-M-Sherlock/ZhiHuArchive" target="_blank" rel="noopener noreferrer">ZhiHuArchive</a> 渲染，模板参考 <a href="https://github.com/frostming/fxzhihu" target="_blank" rel="noopener noreferrer">FxZhihu</a>。
        </p>
    </footer>
    <script src="https://giscus.app/client.js"
            data-repo="L-M-Sherlock/ZhiHuArchive"
            data-repo-id="MDEwOlJlcG9zaXRvcnkzNDk5NDE0MzM="
            data-category="Announcements"
            data-category-id="DIC_kwDOFNuuuc4Ck92x"
            data-mapping="title"
            data-strict="0"
            data-reactions-enabled="1"
            data-emit-metadata="0"
            data-input-position="top"
            data-theme="preferred_color_scheme"
            data-lang="zh-CN"
            data-loading="lazy"
            crossorigin="anonymous"
            async>
    </script>
</body>
</html>"""

rss_article_template = """<main>
<header>
    <img class="origin_image" src="${"image_url"}"/>
</header>
<article>
    ${"content"}
    ${"reference"}
</article>
<footer>
    <p>发表于 ${"created_time_formatted"}</p>
</footer>
</main>"""


def fill_article_template(data: dict, is_rss: bool = False) -> str:
    template = rss_article_template if is_rss else article_template
    archive_url_value = archive_url(file.stem)
    source_url_value = source_url(data, file.stem)
    author_url_value = normalize_author_url(data["author"].get("url", ""))
    title = clean_text(data["title"])
    author_name = clean_text(data["author"]["name"])
    meta_description = build_meta_description(
        data.get("excerpt", ""),
        data.get("content", ""),
    )
    json_ld = json_ld_script(
        article_schema(
            title=title,
            description=meta_description,
            archive_url_value=archive_url_value,
            author_name=author_name,
            author_url_value=author_url_value,
            published_timestamp=data["created"],
            modified_timestamp=data.get("updated") or data["created"],
            image_url=data.get("image_url", ""),
        )
    )
    return (
        template.replace('${"title"}', html_attr(title))
        .replace('${"archive_url"}', html_attr(archive_url_value))
        .replace('${"source_url"}', html_attr(source_url_value))
        .replace('${"meta_description"}', html_attr(meta_description))
        .replace('${"json_ld"}', json_ld)
        .replace('${"redirect"}', "false")
        .replace('${"image_url"}', html_attr(data["image_url"]))
        .replace('${"avatar_url"}', html_attr(data["author"]["avatar_url"]))
        .replace('${"author_url"}', html_attr(author_url_value))
        .replace('${"author"}', html_attr(author_name))
        .replace('${"headline"}', html_attr(clean_text(data["author"]["headline"])))
        .replace('${"created_time"}', html_attr(created_time_str))
        .replace('${"created_time_formatted"}', html_attr(created_time_formatted))
        .replace('${"voteup_count"}', str(data["voteup_count"]))
        .replace('${"comment_count"}', str(data["comment_count"]))
        .replace('${"content"}', data["content"])
        .replace('${"reference"}', extract_reference(data["content"]))
        .replace(
            '${"column_title"}',
            html_attr(data.get("column", {}).get("title", "无")),
        )
        .replace(
            '${"column_description"}',
            html_attr(data.get("column", {}).get("description", "")),
        )
        .replace("    ", "")
    )


Path("html").mkdir(exist_ok=True)

for file in tqdm(list(Path("article").glob("*.json"))):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Format the created timestamp
    created_time = datetime.fromtimestamp(data["created"])
    created_time_str = created_time.isoformat()
    created_time_formatted = created_time.strftime("%Y年%m月%d日")

    data["content"] = process_content(data["content"])

    # Prepare the HTML content
    html_content = fill_article_template(data)
    # Write the rendered HTML to file
    output_file = Path("html") / f"{file.stem}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    rss_content = fill_article_template(data, is_rss=True)

    add_item(data, rss_content)

question_template = """<div style="margin: 0; padding: 0.5em 1em; border-left: 4px solid #999; font-size: 0.86em; background: #f9f9f9;">
<h2>问题描述</h2>
${"question"}
</div>
<hr>"""


answer_template = """<!DOCTYPE html>
<html lang="zh">
<head>
    <title>${"title"} - @${"author"} | ZhiHu Archive</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} - @${"author"} | ZhiHu Archive">
    <meta property="og:site_name" content="ZhiHu Archive for Thoughts Memo">
    <meta property="og:description" itemprop="description" content="${"meta_description"}">
    <meta property="og:url" content="${"archive_url"}">
    <meta name="description" content="${"meta_description"}">
    <meta data-pagefind-meta="title" content="${"title"}">
    <link rel="stylesheet" href="https://gcore.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" content="${"title"} - @${"author"} | ZhiHu Archive">
    <meta name="twitter:description" content="${"meta_description"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <meta name="google-site-verification" content="U7ZAFUgGNK60mmMqaRygg5vy-k8pwbPbDFXNjDCu7Xk" />
    <link rel="canonical" href="${"archive_url"}">
    <link rel="alternate" type="application/rss+xml" title="ZhiHu Archive for Thoughts Memo" href="https://l-m-sherlock.github.io/ZhiHuArchive/feed.xml">
    ${"json_ld"}
    <script>
        const redirect = ${"redirect"};
        if (redirect) {
            window.location.replace("${"source_url"}");
        }
    </script>
    <style>
        img {
            vertical-align: middle;
        }
        figure img {
            width: 100%;
        }
        figure {
            margin: 1.4em 0;
        }
        .author {
            display: flex;
            gap: 1em;
            align-items: center;
        }
        #avatar {
            width: 100px;
            height: 100px;
        }
        .author > div {
            flex: 1;
        }
        a {
            color: #2563eb;
            text-decoration: none;
            border-bottom: 1px solid rgba(37, 99, 235, 0.3);
            border-radius: 4px;
            padding: 0 0.1em;
            transition: color 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
        }
        a:hover,
        a:focus-visible {
            color: #1d4ed8;
            border-bottom-color: rgba(29, 78, 216, 0.6);
            background-color: rgba(37, 99, 235, 0.08);
        }
        a:focus-visible {
            outline: none;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25);
        }
        a[data-draft-type="link-card"] {
           display: block;
           border-bottom: none;
           padding: 0;
           background: none;
        }
        .references {
            font-size: 0.85em;
        }
        .formula-display {
            display: block;
            text-align: center;
        }
    </style>
</head>
<body style="max-width: 1000px; margin: 0 auto; padding: 0 1em 0 1em;" class="yue">
    <p data-pagefind-ignore><a href="./">← 返回目录</a></p>
    <hr>
    <header>
        <h1><a href="${"source_url"}" target="_blank" rel="noopener noreferrer">${"title"}</a></h1>
        <div class="author">
            <img class="avatar" id="avatar" src="${"avatar_url"}" />
            <div>
                <h2 rel="author">
                    <a href="${"author_url"}" target="_blank" rel="noopener noreferrer">@${"author"}</a>
                </h2>
                <p>${"headline"}</p>
            </div>
        </div>
        <time datetime="${"created_time"}">发表于 ${"created_time_formatted"}</time>
        <p rel="stats"style="color: #999; font-size: 0.9em;">${"voteup_count"} 👍 / ${"comment_count"} 💬</p>
    </header>
    <article data-pagefind-body>
        ${"question"}
        ${"content"}
        ${"reference"}
        <hr>
        <p data-pagefind-ignore><a href="./">← 返回目录</a></p>
    </article>
    <footer>
        <p style="color: #999; font-size: 0.85em; text-align: center; margin-top: 2em;">
            本页面由 <a href="https://github.com/L-M-Sherlock/ZhiHuArchive" target="_blank" rel="noopener noreferrer">ZhiHuArchive</a> 渲染，模板参考 <a href="https://github.com/frostming/fxzhihu" target="_blank" rel="noopener noreferrer">FxZhihu</a>。
        </p>
    </footer>
    <script src="https://giscus.app/client.js"
            data-repo="L-M-Sherlock/ZhiHuArchive"
            data-repo-id="MDEwOlJlcG9zaXRvcnkzNDk5NDE0MzM="
            data-category="Announcements"
            data-category-id="DIC_kwDOFNuuuc4Ck92x"
            data-mapping="title"
            data-strict="0"
            data-reactions-enabled="1"
            data-emit-metadata="0"
            data-input-position="top"
            data-theme="preferred_color_scheme"
            data-lang="zh-CN"
            data-loading="lazy"
            crossorigin="anonymous"
            async>
    </script>
</body>
</html>"""

rss_answer_template = """<main>
<article>
    ${"question"}
    ${"content"}
    ${"reference"}
</article>
<footer>
    <p>发表于 ${"created_time_formatted"}</p>
    <div class="stats">${"voteup_count"} 👍 / ${"comment_count"} 💬</div>
    <div class="author">
        <img class="avatar" id="avatar" src="${"avatar_url"}" />
        <div>
            <h2 rel="author">
                <a href="${"author_url"}" target="_blank">@${"author"}</a>
            </h2>
        </div>
    </div>
</footer>
</main>"""


def fill_answer_template(data: dict, is_rss: bool = False) -> str:
    template = rss_answer_template if is_rss else answer_template
    question_detail = data["question"].get("detail", "")
    question_block = ""
    if question_detail and question_detail.strip():
        question_block = question_template.replace(
            '${"question"}',
            process_content(question_detail),
        )
    archive_url_value = archive_url(file.stem)
    source_url_value = source_url(data, file.stem)
    author_url_value = normalize_author_url(data["author"].get("url", ""))
    title = clean_text(data["question"]["title"])
    author_name = clean_text(data["author"]["name"])
    meta_description = build_meta_description(
        data.get("excerpt", ""),
        data["question"].get("title", ""),
        question_detail,
        data.get("content", ""),
    )
    json_ld = json_ld_script(
        article_schema(
            title=title,
            description=meta_description,
            archive_url_value=archive_url_value,
            author_name=author_name,
            author_url_value=author_url_value,
            published_timestamp=data["created_time"],
            modified_timestamp=data.get("updated_time") or data["created_time"],
        )
    )
    return (
        template.replace('${"title"}', html_attr(title))
        .replace('${"archive_url"}', html_attr(archive_url_value))
        .replace('${"source_url"}', html_attr(source_url_value))
        .replace('${"meta_description"}', html_attr(meta_description))
        .replace('${"json_ld"}', json_ld)
        .replace('${"redirect"}', "false")
        .replace('${"avatar_url"}', html_attr(data["author"]["avatar_url"]))
        .replace('${"author_url"}', html_attr(author_url_value))
        .replace('${"author"}', html_attr(author_name))
        .replace('${"headline"}', html_attr(clean_text(data["author"]["headline"])))
        .replace('${"created_time"}', html_attr(created_time_str))
        .replace('${"created_time_formatted"}', html_attr(created_time_formatted))
        .replace('${"voteup_count"}', str(data["voteup_count"]))
        .replace('${"comment_count"}', str(data["comment_count"]))
        .replace('${"question"}', question_block)
        .replace('${"content"}', data["content"])
        .replace('${"reference"}', extract_reference(data["content"]))
        .replace("    ", "")
    )


for file in tqdm(list(Path("answer").glob("*.json"))):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "error" in data:
        print(data["error"], file.stem)
        continue

    # Format the created timestamp
    created_time = datetime.fromtimestamp(data["created_time"])
    created_time_str = created_time.isoformat()
    created_time_formatted = created_time.strftime("%Y年%m月%d日")

    data["content"] = process_content(data["content"])

    # Prepare the HTML content
    html_content = fill_answer_template(data)
    # Write the rendered HTML to file
    output_file = Path("html") / f"{file.stem}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    rss_content = fill_answer_template(data, is_rss=True)

    add_item(data, rss_content)

# Generate RSS feed
fg.atom_file(Path("html") / "feed.xml")
