import json
from pathlib import Path
from datetime import datetime, timezone

BASE_URL = "https://l-m-sherlock.github.io/ZhiHuArchive"

# Load censorship data
with open("censorship.json", "r", encoding="utf-8") as f:
    censorship_data = json.load(f)

# Collect all articles
articles = []
for file in Path("article").glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        data["file_stem"] = file.stem
        articles.append(data)

# Collect all answers
answers = []
for file in Path("answer").glob("*.json"):
    with open(file, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            data["file_stem"] = file.stem
            if "error" in data:
                print(data["error"], file.stem)
                continue
            answers.append(data)
        except json.JSONDecodeError:
            print(file.stem, "is not a valid json file")

# Sort by voteup_count
articles.sort(key=lambda x: x["voteup_count"], reverse=True)
answers.sort(key=lambda x: x["voteup_count"], reverse=True)

# Generate HTML content with tabs
html_content = (
    """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thoughts Memo 和 Jarrett Ye 的知乎备份</title>
    <meta property="og:type" content="website">
    <meta property="og:title" content="Thoughts Memo 和 Jarrett Ye 的知乎备份">
    <meta property="og:site_name" content="ZhiHu Archive for Thoughts Memo and Jarrett Ye">
    <meta property="og:url" content="https://l-m-sherlock.github.io/ZhiHuArchive/">
    <meta name="description" property="og:description" content="Thoughts Memo 和 Jarrett Ye 的知乎文章和回答备份目录">
    <meta name="google-site-verification" content="U7ZAFUgGNK60mmMqaRygg5vy-k8pwbPbDFXNjDCu7Xk" />
    <meta property="twitter:card" content="summary">
    <meta name="twitter:title" property="og:title" itemprop="name" content="Thoughts Memo 和 Jarrett Ye 的知乎备份">
    <meta name="twitter:description" property="og:description" itemprop="description" content="Thoughts Memo 和 Jarrett Ye 的知乎文章和回答备份目录">
    <style>
        body { max-width: 800px; margin: 0 auto; padding: 20px; }
        .item { margin: 10px 0; }
        .votes { color: #666; font-size: 0.9em; }
        .created_time { color: #999; font-size: 0.9em; }
        .censored { background-color: #ffeb3b; }

        /* Tab styles */
        .tabs { margin-bottom: 20px; }
        .tab-button {
            padding: 10px 20px;
            border: none;
            background: #f0f0f0;
            cursor: pointer;
            font-size: 16px;
        }
        .tab-button.active {
            background: #007bff;
            color: white;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
    </style>
    <script>
        function openTab(evt, tabName) {
            var tabContents = document.getElementsByClassName("tab-content");
            for (var i = 0; i < tabContents.length; i++) {
                tabContents[i].classList.remove("active");
            }
            var tabButtons = document.getElementsByClassName("tab-button");
            for (var i = 0; i < tabButtons.length; i++) {
                tabButtons[i].classList.remove("active");
            }
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }
    </script>
</head>
<body>
"""
    + f"""
    <h1>Thoughts Memo 和 Jarrett Ye 的知乎备份</h1>
    <p>
        <a href="https://github.com/l-m-sherlock/ZhiHuArchive" target="_blank" rel="noopener noreferrer">
            <img src="https://img.shields.io/github/stars/l-m-sherlock/ZhiHuArchive?style=social" alt="GitHub stars">
        </a>
    </p>
    <p>RSS: <a href="./feed.xml" target="_blank" rel="noopener noreferrer">Atom Feed</a></p>

    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'articles-tab')">文章 ({len(articles)})</button>
        <button class="tab-button" onclick="openTab(event, 'answers-tab')">回答 ({len(answers)})</button>
    </div>

    <div id="articles-tab" class="tab-content active">
        <h2>文章</h2>
"""
)

# Add articles
for article in articles:
    article_path = f"/p/{article['file_stem']}"
    is_censored = censorship_data.get(article_path, False)
    censored_class = "censored" if is_censored else ""
    censored_text = " (censored)" if is_censored else ""
    html_content += f"""
        <div class="item">
            <a href="./{article['file_stem']}.html" class="{censored_class}" target="_blank" rel="noopener noreferrer">{article['title']}{censored_text}</a>
            <span class="votes">({article['voteup_count']} 赞同)</span>
            <span class="created_time">({datetime.fromtimestamp(article['created']).strftime('%Y-%m-%d')})</span>
        </div>
"""

html_content += """
    </div>

    <div id="answers-tab" class="tab-content">
        <h2>回答</h2>
"""

# Add answers
for answer in answers:
    question_title = (
        answer["question"]["title"]
        if "question" in answer and "title" in answer["question"]
        else "Untitled"
    )
    answer_path = f"/answer/{answer['file_stem']}"
    is_censored = censorship_data.get(answer_path, False)
    censored_class = "censored" if is_censored else ""
    censored_text = " (censored)" if is_censored else ""

    html_content += f"""
        <div class="item">
            <a href="./{answer['file_stem']}.html" class="{censored_class}" target="_blank" rel="noopener noreferrer">{question_title}{censored_text}</a>
            <span class="votes">({answer['voteup_count']} 赞同)</span>
            <span class="created_time">({datetime.fromtimestamp(answer['created_time']).strftime('%Y-%m-%d')})</span>
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

# Write the HTML file
with open("./html/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)


def generate_sitemap(articles, answers):
    """Generate sitemap.xml file"""
    sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    # Add index page
    sitemap_content += f"""  <url>
    <loc>{BASE_URL}/</loc>
    <lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    # Add articles
    for article in articles:
        created_time = datetime.fromtimestamp(article["created"], timezone.utc)
        sitemap_content += f"""  <url>
    <loc>{BASE_URL}/{article['file_stem']}.html</loc>
    <lastmod>{created_time.strftime('%Y-%m-%d')}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n"""

    # Add answers
    for answer in answers:
        created_time = datetime.fromtimestamp(answer["created_time"], timezone.utc)
        sitemap_content += f"""  <url>
    <loc>{BASE_URL}/{answer['file_stem']}.html</loc>
    <lastmod>{created_time.strftime('%Y-%m-%d')}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n"""

    sitemap_content += "</urlset>"

    # Write sitemap file
    with open("./html/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_content)


# Add after writing index.html
generate_sitemap(articles, answers)
