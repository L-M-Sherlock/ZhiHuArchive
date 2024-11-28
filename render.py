import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
from feedgen.feed import FeedGenerator
import zoneinfo
from bs4 import BeautifulSoup


article_ids = [file.stem for file in Path("./article").glob("*.json")]
answer_ids = [file.stem for file in Path("./answer").glob("*.json")]

fg = FeedGenerator()
fg.id("https://l-m-sherlock.github.io/ZhiHuArchive/feed.xml")
fg.title("Thoughts Memo")
fg.link(href="https://l-m-sherlock.github.io/ZhiHuArchive/", rel="self")
fg.description("知乎账号 @Thoughts Memo 和 @Jarrett Ye 的文章和回答的存档")
fg.language("zh-Hans")
fg.generator("feedgen", uri="https://github.com/lkiesow/python-feedgen")
fg.icon("https://l-m-sherlock.github.io/ZhiHuArchive/favicon.ico")
fg.logo("https://l-m-sherlock.github.io/ZhiHuArchive/favicon.ico")


def add_item(data, full_html):
    created_timestamp = datetime.fromtimestamp(
        data["created"] if "created" in data else data["created_time"],
        zoneinfo.ZoneInfo("Asia/Shanghai"),
    )
    title = data["question"]["title"] if "question" in data else data["title"]
    fe = fg.add_entry()
    fe.title(title)
    fe.link(
        href=f"https://l-m-sherlock.github.io/ZhiHuArchive/{file.stem}.html",
        rel="alternate",
    )
    fe.link(href=f"https://zhuanlan.zhihu.com/p/{data['id']}", rel="related")
    fe.content(full_html, type="html")
    fe.summary(data["excerpt"])
    fe.published(created_timestamp)
    fe.guid(f"https://l-m-sherlock.github.io/ZhiHuArchive/{file.stem}.html")


def replace_url(url: str) -> str:
    _id = url.split("/")[-1]
    if _id in article_ids or _id in answer_ids:
        return f"./{_id}.html"
    return url


def process_content(content: str) -> str:
    # Parse HTML content
    soup = BeautifulSoup(content, 'html.parser')
    
    # Process img tags
    for img in soup.find_all('img'):
        actualsrc = img.get('data-actualsrc')
        if actualsrc:
            img['src'] = actualsrc
            del img['data-actualsrc']
    
    # Process anchor tags
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and href.startswith('https://link.zhihu.com/'):
            try:
                # Convert relative URL to absolute
                full_url = 'https:' + href if href.startswith('//') else href
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(full_url)
                target = parse_qs(parsed.query).get('target', [None])[0]
                if target:
                    decoded_target = target.replace('https%3A', 'https:').replace('http%3A', 'http:')
                    a['href'] = replace_url(decoded_target)
            except Exception as e:
                print(f"Failed to parse URL {href}: {e}")
                continue
        elif href:
            a['href'] = replace_url(href)
    
    # Remove u tags but keep their contents
    for u in soup.find_all('u'):
        u.unwrap()
    
    return str(soup)


def extract_reference(html: str) -> str:
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    references = {}

    # Find all sup elements and collect references
    for sup in soup.find_all('sup'):
        text = sup.get('data-text')
        url = sup.get('data-url')
        numero = sup.get('data-numero')
        
        if text and url and numero:
            references[numero] = {
                "text": text,
                "url": replace_url(url)
            }

    # Generate reference list if any references were found
    if references:
        reference_list = [
            f'{index}. {ref["text"]} <a href="{ref["url"]}">{ref["url"]}</a>'
            for index, ref in sorted(references.items(), key=lambda item: int(item[0]))
        ]
        return f'<hr><section><h2>参考</h2>{"<br>".join(reference_list)}</section>'

    return ""


# Create HTML template
article_template = """<!DOCTYPE html>
<html lang="zh">
<head>
    <title>${"title"} - @${"author"}</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} - @${"author"}">
    <meta property="og:site_name" content="ZhiHu Archive for Thoughts Memo">
    <meta property="og:url" content="${"url"}">
    <meta name="description" property="og:description" content="${"excerpt"}">
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" property="og:title" itemprop="name" content="${"title"} - @${"author"}">
    <meta name="twitter:description" property="og:description" itemprop="description" content="${"excerpt"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <meta name="google-site-verification" content="U7ZAFUgGNK60mmMqaRygg5vy-k8pwbPbDFXNjDCu7Xk" />
    <link rel="alternate" type="application/rss+xml" title="ZhiHu Archive for Thoughts Memo" href="https://l-m-sherlock.github.io/ZhiHuArchive/feed.xml">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    <script>
    </script>
    <style>
        .origin_image {
            width: 100%;
        }
        figure {
            margin:1.4em 0;
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
        }
        #avatar {
            width: 100px;
            height: 100px;
        }
        .author > div {
            flex: 1;
        }
        a[data-draft-type="link-card"] {
           display: block;
        }
    </style>
</head>
<body style="max-width: 1000px; margin: 0 auto; padding: 0 1em 0 1em;" class="yue">
    <p><a href="./">← 返回目录</a></p>
    <hr>
    <header>
        <img class="origin_image" src="${"image_url"}"/>
        <h1><a href="${"url"}">${"title"}</a></h1>
        <div class="author">
            <img class="avatar" id="avatar" src="${"avatar_url"}" />
            <div>
                <h2 rel="author">
                    <a href="${"author_url"}" target="_blank">@${"author"}</a>
                </h2>
                <p> ${"headline"} </p>
            </div>
        </div>
        <time datetime="${"created_time"}">发表于 ${"created_time_formatted"}</time>
        <p rel="stats"style="color: #999; font-size: 0.9em;">${"voteup_count"} 👍 / ${"comment_count"} 💬</p>
    </header>
    <article>
        ${"content"}
        ${"reference"}
        <hr>
        <div class="column" style="margin: 1em 0; padding: 0.5em 1em; border: 2px solid #999; border-radius: 5px;">
            <h2>专栏：${"column_title"}</h2>
        </div>
        <hr>
        <p><a href="./">← 返回目录</a></p>
    </article>
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
    return (
        template.replace('${"title"}', data["title"])
        .replace('${"url"}', f"https://zhuanlan.zhihu.com/p/{file.stem}")
        .replace('${"excerpt"}', data["excerpt"])
        .replace('${"redirect"}', "false")
        .replace('${"image_url"}', data["image_url"])
        .replace('${"avatar_url"}', data["author"]["avatar_url"])
        .replace('${"author_url"}', data["author"]["url"])
        .replace('${"author"}', data["author"]["name"])
        .replace('${"headline"}', data["author"]["headline"])
        .replace('${"created_time"}', created_time_str)
        .replace('${"created_time_formatted"}', created_time_formatted)
        .replace('${"voteup_count"}', str(data["voteup_count"]))
        .replace('${"comment_count"}', str(data["comment_count"]))
        .replace('${"content"}', data["content"])
        .replace('${"reference"}', extract_reference(data["content"]))
        .replace('${"column_title"}', data["column"]["title"])
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
    <title>${"title"} - @${"author"}</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} - @${"author"}">
    <meta property="og:site_name" content="ZhiHu Archive for Thoughts Memo">
    <meta property="og:url" content="${"url"}">
    <meta name="description" property="og:description" content="${"excerpt"}">
	<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" property="og:title" itemprop="name" content="${"title"} - @${"author"}">
    <meta name="twitter:description" property="og:description" itemprop="description" content="${"excerpt"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <meta name="google-site-verification" content="U7ZAFUgGNK60mmMqaRygg5vy-k8pwbPbDFXNjDCu7Xk" />
    <link rel="alternate" type="application/rss+xml" title="ZhiHu Archive for Thoughts Memo" href="https://l-m-sherlock.github.io/ZhiHuArchive/feed.xml">
    <script>
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
        }
        #avatar {
            width: 100px;
            height: 100px;
        }
        .author > div {
            flex: 1;
        }
        a[data-draft-type="link-card"] {
           display: block;
        }
    </style>
</head>
<body style="max-width: 1000px; margin: 0 auto; padding: 0 1em 0 1em;" class="yue">
    <p><a href="./">← 返回目录</a></p>
    <hr>
    <header>
        <h1><a href="${"url"}">${"title"}</a></h1>
        <div class="author">
            <img class="avatar" id="avatar" src="${"avatar_url"}" />
            <div>
                <h2 rel="author">
                    <a href="${"author_url"}" target="_blank">@${"author"}</a>
                </h2>
                <p> ${"headline"} </p>
            </div>
        </div>
        <time datetime="${"created_time"}">发表于 ${"created_time_formatted"}</time>
        <p rel="stats"style="color: #999; font-size: 0.9em;">${"voteup_count"} 👍 / ${"comment_count"} 💬</p>
    </header>
    <article>
        ${"question"}
        ${"content"}
        ${"reference"}
        <hr>
        <p><a href="./">← 返回目录</a></p>
    </article>
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
    return (
        template.replace('${"title"}', data["question"]["title"])
        .replace(
            '${"url"}',
            f"https://www.zhihu.com/question/{data['question']['id']}/answer/{file.stem}",
        )
        .replace('${"excerpt"}', data["excerpt"])
        .replace('${"redirect"}', "false")
        .replace('${"avatar_url"}', data["author"]["avatar_url"])
        .replace('${"author_url"}', data["author"]["url"])
        .replace('${"author"}', data["author"]["name"])
        .replace('${"headline"}', data["author"]["headline"])
        .replace('${"created_time"}', created_time_str)
        .replace('${"created_time_formatted"}', created_time_formatted)
        .replace('${"voteup_count"}', str(data["voteup_count"]))
        .replace('${"comment_count"}', str(data["comment_count"]))
        .replace(
            '${"question"}',
            question_template.replace('${"question"}', data["question"]["detail"]),
        )
        .replace('${"question"}', data["question"]["detail"])
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
