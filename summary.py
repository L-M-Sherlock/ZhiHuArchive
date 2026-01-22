import json
import re
import shutil
from pathlib import Path
from datetime import datetime, timezone

from bs4 import BeautifulSoup

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


def html_to_text(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def build_search_index(articles: list, answers: list) -> list:
    docs = []
    for article in articles:
        docs.append(
            {
                "id": f"article-{article['file_stem']}",
                "url": f"./{article['file_stem']}.html",
                "title": article.get("title", ""),
                "excerpt": html_to_text(article.get("excerpt", "")),
                "content": html_to_text(article.get("content", "")),
                "image": article.get("image_url", ""),
                "created": article.get("created", 0),
                "type": "article",
            }
        )
    for answer in answers:
        question = answer.get("question", {})
        question_title = question.get("title", "Untitled")
        question_detail = html_to_text(question.get("detail", ""))
        content_text = html_to_text(answer.get("content", ""))
        docs.append(
            {
                "id": f"answer-{answer['file_stem']}",
                "url": f"./{answer['file_stem']}.html",
                "title": question_title,
                "excerpt": html_to_text(answer.get("excerpt", "")),
                "content": f"{question_detail} {content_text}".strip(),
                "image": "",
                "created": answer.get("created_time", 0),
                "type": "answer",
            }
        )
    return docs


search_script = """<script type="module">
    const input = document.getElementById("search-input");
    const metaEl = document.getElementById("search-meta");
    const resultsEl = document.getElementById("search-results");
    const moreButton = document.getElementById("search-more");

    const hasCJK = (text) => /[\\u3040-\\u30ff\\u3400-\\u9fff\\uf900-\\ufaff]/.test(text);

    const getBasePath = () => {
        const url = new URL(window.location.href);
        let basePath = url.pathname;
        if (!basePath.endsWith("/")) {
            basePath = basePath.substring(0, basePath.lastIndexOf("/") + 1);
        }
        return basePath;
    };

    const basePath = getBasePath();
    const indexUrl = basePath + "search-index.json";
    const segmentitScript = basePath + "segmentit.js";

    let segmenter = null;
    let segmenterPromise = null;
    let indexData = null;
    let indexPromise = null;
    let lastResults = [];
    let lastRendered = 0;
    let lastSearchToken = 0;
    const pageSize = 10;
    const maxResults = 200;
    const minCjkLength = 2;

    const shouldSegment = (term) =>
        hasCJK(term) && !/\\s/.test(term) && term.trim().length >= minCjkLength;

    const initSegmenter = () => {
        const lib = window.segmentit || window.Segmentit;
        if (!lib) {
            return null;
        }
        const Segment = lib.Segment || (lib.default && lib.default.Segment);
        const useDefault = lib.useDefault || (lib.default && lib.default.useDefault);
        if (!Segment || !useDefault) {
            return null;
        }
        return useDefault(new Segment());
    };

    const loadSegmenter = () =>
        new Promise((resolve) => {
            const existing = initSegmenter();
            if (existing) {
                resolve(existing);
                return;
            }
            const script = document.createElement("script");
            script.src = segmentitScript;
            script.async = true;
            script.onload = () => resolve(initSegmenter());
            script.onerror = () => resolve(null);
            document.head.appendChild(script);
        });

    const ensureSegmenter = (term) => {
        if (!shouldSegment(term)) {
            return null;
        }
        if (segmenter) {
            return Promise.resolve(segmenter);
        }
        if (!segmenterPromise) {
            segmenterPromise = loadSegmenter().then((loaded) => {
                segmenter = loaded;
                return loaded;
            });
        }
        return segmenterPromise;
    };

    const segmentText = (text) => {
        if (!segmenter) {
            return [];
        }
        try {
            return segmenter
                .doSegment(text)
                .map((token) => token.w || token.word || "")
                .filter((token) => token && token.trim());
        } catch (error) {
            return [];
        }
    };

    const ensureIndex = () => {
        if (indexData) {
            return Promise.resolve(indexData);
        }
        if (!indexPromise) {
            indexPromise = fetch(indexUrl)
                .then((response) => response.json())
                .then((data) => {
                    indexData = data.map((doc) => {
                        const title = doc.title || "";
                        const excerpt = doc.excerpt || "";
                        const content = doc.content || "";
                        return {
                            ...doc,
                            titleLower: title.toLowerCase(),
                            searchText: (title + " " + excerpt + " " + content).toLowerCase(),
                        };
                    });
                    return indexData;
                });
        }
        return indexPromise;
    };

    const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&");
    const escapeHtml = (value) =>
        value
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");

    const buildQuery = (term) => {
        const trimmed = term.trim();
        const lower = trimmed.toLowerCase();
        const phrases = [];
        const phraseRegex = /"([^"]+)"/g;
        let remaining = trimmed;
        let match;
        while ((match = phraseRegex.exec(trimmed)) !== null) {
            if (match[1]) {
                phrases.push(match[1]);
            }
        }
        if (phrases.length) {
            remaining = trimmed.replace(phraseRegex, " ").trim();
        }
        let tokens = remaining ? remaining.split(/\\s+/).filter(Boolean) : [];
        if (!tokens.length && shouldSegment(trimmed) && segmenter) {
            tokens = segmentText(trimmed);
        }
        if (!tokens.length && trimmed) {
            tokens = [trimmed];
        }
        const tokensLower = tokens.map((token) => token.toLowerCase());
        const phrasesLower = phrases.map((phrase) => phrase.toLowerCase());
        const highlightTerms = [...phrasesLower, ...tokensLower]
            .filter((value) => value && value.length >= minCjkLength)
            .slice(0, 8);
        return { raw: trimmed, lower, tokens: tokensLower, phrases: phrasesLower, highlights: highlightTerms };
    };

    const matchesDoc = (doc, query) => {
        const text = doc.searchText || "";
        if (query.phrases.length && query.phrases.some((phrase) => !text.includes(phrase))) {
            return false;
        }
        if (query.tokens.length && query.tokens.some((token) => !text.includes(token))) {
            return false;
        }
        return true;
    };

    const scoreDoc = (doc, query) => {
        let score = 0;
        const title = doc.titleLower || "";
        if (query.raw && title.includes(query.lower)) {
            score += 100;
        }
        query.phrases.forEach((phrase) => {
            if (title.includes(phrase)) {
                score += 60;
            } else if (doc.searchText.includes(phrase)) {
                score += 20;
            }
        });
        query.tokens.forEach((token) => {
            if (!token) {
                return;
            }
            if (title.includes(token)) {
                score += 20;
            } else if (doc.searchText.includes(token)) {
                score += 4;
            }
        });
        return score;
    };

    const highlightText = (text, terms) => {
        if (!terms.length) {
            return escapeHtml(text);
        }
        let output = escapeHtml(text);
        terms.forEach((term) => {
            if (!term) {
                return;
            }
            const regex = new RegExp(escapeRegExp(term), "gi");
            output = output.replace(regex, "<mark>$&</mark>");
        });
        return output;
    };

    const clearResults = () => {
        resultsEl.innerHTML = "";
        metaEl.textContent = "";
        moreButton.style.display = "none";
        lastResults = [];
        lastRendered = 0;
    };

    const renderBatch = () => {
        const slice = lastResults.slice(lastRendered, lastRendered + pageSize);
        slice.forEach((item) => {
            const doc = item.doc;
            const li = document.createElement("li");
            li.className = "search-result";
            const title = doc.title || doc.url || "未命名";
            const thumb = doc.image
                ? `<div class="search-result-thumb"><img src="${doc.image}" alt="${title}"></div>`
                : "";
            const snippetSource = doc.excerpt || doc.content || "";
            const snippet = snippetSource.length > 220 ? snippetSource.slice(0, 220) + "..." : snippetSource;
            const highlightedSnippet = highlightText(snippet, item.highlights);
            li.innerHTML = `${thumb}<div class="search-result-body">
                <p class="search-result-title"><a href="${doc.url}" target="_blank" rel="noopener noreferrer">${title}</a></p>
                <p class="search-result-excerpt">${highlightedSnippet}</p>
            </div>`;
            resultsEl.appendChild(li);
        });
        lastRendered += slice.length;
        if (lastRendered >= lastResults.length) {
            moreButton.style.display = "none";
        } else {
            moreButton.style.display = "inline-flex";
        }
    };

    const searchAndRender = async (term) => {
        const token = ++lastSearchToken;
        const trimmed = term.trim();
        if (!trimmed) {
            clearResults();
            return;
        }
        metaEl.textContent = "正在加载索引…";
        const docs = await ensureIndex();
        if (token !== lastSearchToken) {
            return;
        }
        const segmentPromise = ensureSegmenter(trimmed);
        const query = buildQuery(trimmed);

        const matches = [];
        for (const doc of docs) {
            if (matchesDoc(doc, query)) {
                matches.push({ doc, score: scoreDoc(doc, query), highlights: query.highlights });
            }
        }
        matches.sort((a, b) => (b.score - a.score) || (b.doc.created - a.doc.created));
        lastResults = matches.slice(0, maxResults);
        lastRendered = 0;
        resultsEl.innerHTML = "";

        if (!lastResults.length) {
            metaEl.textContent = `没有找到与“${trimmed}”相关的结果`;
            moreButton.style.display = "none";
        } else {
            metaEl.textContent = `找到 ${lastResults.length} 个与“${trimmed}”相关的结果`;
            renderBatch();
        }

        if (segmentPromise && !segmenter) {
            segmentPromise.then((loaded) => {
                if (!loaded) {
                    return;
                }
                if (token !== lastSearchToken) {
                    return;
                }
                if (input.value.trim() === trimmed) {
                    searchAndRender(trimmed);
                }
            });
        }
    };

    const debounce = (fn, delay = 300) => {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    };

    const init = () => {
        input.addEventListener("input", debounce((event) => {
            searchAndRender(event.target.value);
        }));
        moreButton.addEventListener("click", renderBatch);
    };

    init();
</script>
"""

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
        #search { margin: 24px 0 20px; }
        .search-label {
            display: block;
            font-size: 0.95em;
            color: #4b5563;
            margin-bottom: 6px;
        }
        .search-input {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            font-size: 16px;
            outline: none;
            box-sizing: border-box;
        }
        .search-input:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
        }
        .search-helper {
            margin-top: 6px;
            font-size: 0.85em;
            color: #6b7280;
        }
        .search-helper strong {
            color: #374151;
        }
        .search-meta {
            margin-top: 10px;
            font-size: 0.9em;
            color: #374151;
        }
        .search-results {
            list-style: none;
            padding: 0;
            margin: 12px 0 0;
        }
        .search-result {
            display: flex;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #f3f4f6;
        }
        .search-result-thumb img {
            width: 64px;
            height: 64px;
            object-fit: cover;
            border-radius: 10px;
        }
        .search-result-title {
            margin: 0 0 6px;
            font-size: 1em;
        }
        .search-result-excerpt {
            margin: 0;
            color: #4b5563;
            font-size: 0.9em;
            line-height: 1.4;
        }
        .search-more {
            margin-top: 12px;
            padding: 8px 14px;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            background: #fff;
            cursor: pointer;
            font-size: 0.9em;
        }
        .search-more:hover {
            border-color: #cbd5f5;
            background: #f8fafc;
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
        .badge-link,
        .badge-link:hover,
        .badge-link:focus-visible {
            border: none;
            padding: 0;
            background: none;
        }
        .badge-link:focus-visible {
            box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.35);
            border-radius: 6px;
        }
        .censored {
            background-color: #fef08a;
            border-bottom-color: rgba(202, 138, 4, 0.6);
            color: #1f2937;
        }

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
<body data-pagefind-ignore="all">
"""
    + f"""
    <h1>Thoughts Memo 和 Jarrett Ye 的知乎备份</h1>
    <p>
        <a class="badge-link" href="https://github.com/l-m-sherlock/ZhiHuArchive" target="_blank" rel="noopener noreferrer">
            <img src="https://img.shields.io/github/stars/l-m-sherlock/ZhiHuArchive?style=social" alt="GitHub stars">
        </a>
    </p>
    <p>RSS: <a href="./feed.xml" target="_blank" rel="noopener noreferrer">Atom Feed</a></p>
    <p>NotebookLM 精选笔记：<a href="https://notebooklm.google.com/notebook/dbe190a1-1122-462d-ab4f-40400d9f1d2a" target="_blank" rel="noopener noreferrer">汉化组文章合集</a></p>

    <div id="search">
        <label class="search-label" for="search-input">站内搜索</label>
        <input id="search-input" class="search-input" type="search" placeholder="搜索文章和回答..." autocapitalize="none" enterkeyhint="search">
        <div class="search-helper">提示：首次搜索会加载索引，中文搜索会加载分词库；也支持手动分词（例如：习得性 无助）。</div>
        <div id="search-meta" class="search-meta"></div>
        <ol id="search-results" class="search-results"></ol>
        <button id="search-more" class="search-more" type="button" style="display: none;">加载更多结果</button>
    </div>
    {search_script}

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
Path("html").mkdir(exist_ok=True)
asset_src = Path("assets") / "segmentit.js"
asset_dst = Path("html") / "segmentit.js"
if asset_src.exists():
    shutil.copyfile(asset_src, asset_dst)

with open("./html/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

search_docs = build_search_index(articles, answers)
with open("./html/search-index.json", "w", encoding="utf-8") as f:
    json.dump(search_docs, f, ensure_ascii=False)


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
