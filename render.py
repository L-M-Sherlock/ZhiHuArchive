import json
from pathlib import Path
from datetime import datetime
import re


article_ids = [file.stem for file in Path("./article").glob("*.json")]
answer_ids = [file.stem for file in Path("./answer").glob("*.json")]


def replace_url(url: str) -> str:
    _id = url.split("/")[-1]
    if _id in article_ids or _id in answer_ids:
        return f"./{_id}.html"
    return url


def process_content(content: str) -> str:
    # Remove zhihu redirect links
    content = content.replace("//link.zhihu.com/?target=https%3A", "")
    content = content.replace("//link.zhihu.com/?target=http%3A", "")

    # Replace internal links with local paths
    link_pattern = r"href=\"(.*?)\""
    content = re.sub(
        link_pattern, lambda m: f'href="{replace_url(m.group(1))}"', content
    )

    return content


def extract_reference(html: str) -> str:
    reference_regex = re.compile(
        r'<sup[^>]*data-text="([^"]*)"[^>]*data-url="([^"]*)"[^>]*data-numero="([^"]*)"[^>]*>'
    )
    references = {}

    for match in reference_regex.finditer(html):
        text, url, numero = match.groups()
        references[numero] = {"text": text, "url": replace_url(url)}

    reference_list = [
        f'{index}. {ref["text"]} <a href="{ref["url"]}">{ref["url"]}</a>'
        for index, ref in sorted(references.items(), key=lambda item: int(item[0]))
    ]

    if reference_list:
        return f'<hr><section><h2>参考</h2>{"<br>".join(reference_list)}</section>'
    return ""


# Create HTML template
article_template = """<!DOCTYPE html>
<html lang="zh">
<head>
    <title>${"title"} | FxZhihu</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} | FxZhihu">
    <meta property="og:site_name" content="FxZhihu / Fixup Zhihu">
    <meta property="og:url" content="${"url"}">
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" property="og:title" itemprop="name" content="${"title"} | FxZhihu">
    <meta name="twitter:description" property="og:description" itemprop="description" content="${"excerpt"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    <script>
        const redirect = ${"redirect"};
        if (redirect) {
            window.location.replace("${"url"}");
        }
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
    </article>
</body>
</html>"""

Path("html").mkdir(exist_ok=True)

for file in Path("article").glob("*.json"):
    with open(file, "r") as f:
        data = json.load(f)

    # Format the created timestamp
    created_time = datetime.fromtimestamp(data["created"])
    created_time_str = created_time.isoformat()
    created_time_formatted = created_time.strftime("%Y年%m月%d日")

    data["content"] = process_content(data["content"])

    # Prepare the HTML content
    html_content = (
        article_template.replace('${"title"}', data["title"])
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
    )
    # Write the rendered HTML to file
    output_file = Path("html") / f"{file.stem}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)


answer_template = """<!DOCTYPE html>
<html lang="zh">
<head>
    <title>${"title"} - @${"author"} | FxZhihu</title>
    <meta charset="UTF-8">
    <meta property="og:type" content="website">
    <meta property="og:title" content="${"title"} - @${"author"} | FxZhihu">
    <meta property="og:site_name" content="FxZhihu / Fixup Zhihu">
    <meta property="og:url" content="${"url"}">
	<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/yue.css@0.4.0/yue.css">
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" property="og:title" itemprop="name" content="${"title"} - @${"author"} | FxZhihu">
    <meta name="twitter:description" property="og:description" itemprop="description" content="${"excerpt"}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
    <script>
        const redirect = ${"redirect"};
        if (redirect) {
            window.location.replace("${"url"}");
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
    </article>
</body>
</html>"""

for file in Path("answer").glob("*.json"):
    with open(file, "r") as f:
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
    html_content = (
        answer_template.replace('${"title"}', data["question"]["title"])
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
        .replace('${"question"}', data["question"]["detail"])
        .replace('${"content"}', data["content"])
        .replace('${"reference"}', extract_reference(data["content"]))
    )
    # Write the rendered HTML to file
    output_file = Path("html") / f"{file.stem}.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
