import json
import shutil
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
        <div class="search-helper">提示：已启用<strong>中文分词</strong>（首次中文搜索会加载词库），也支持手动分词（例如：习得性 无助）。结果会先快速展示，再逐步精确筛选。</div>
        <div id="search-meta" class="search-meta"></div>
        <ol id="search-results" class="search-results"></ol>
        <button id="search-more" class="search-more" type="button" style="display: none;">加载更多结果</button>
    </div>
    <script type="module">
        const input = document.getElementById("search-input");
        const metaEl = document.getElementById("search-meta");
        const resultsEl = document.getElementById("search-results");
        const moreButton = document.getElementById("search-more");

        const hasCJK = (text) => /[\\u3040-\\u30ff\\u3400-\\u9fff\\uf900-\\ufaff]/.test(text);

        const getBasePath = () => {{
            const url = new URL(window.location.href);
            let basePath = url.pathname;
            if (!basePath.endsWith("/")) {{
                basePath = basePath.substring(0, basePath.lastIndexOf("/") + 1);
            }}
            return basePath;
        }};

        const basePath = getBasePath();
        const segmentitScript = `${{basePath}}segmentit.js`;
        let pagefind = null;
        let segmenter = null;
        let segmenterPromise = null;
        let lastResults = [];
        let lastRawResults = [];
        let lastQuery = "";
        let lastRendered = 0;
        let lastSearchToken = 0;
        const dataCache = new Map();
        const pageSize = 8;
        const maxScan = 30;
        const minCjkLength = 2;

        const shouldSegment = (term) =>
            hasCJK(term) && !/\\s/.test(term) && term.trim().length >= minCjkLength;

        const initSegmenter = () => {{
            const lib = window.segmentit || window.Segmentit;
            if (!lib) {{
                return null;
            }}
            const Segment = lib.Segment || lib.default?.Segment;
            const useDefault = lib.useDefault || lib.default?.useDefault;
            if (!Segment || !useDefault) {{
                return null;
            }}
            return useDefault(new Segment());
        }};

        const loadSegmenter = () =>
            new Promise((resolve) => {{
                const existing = initSegmenter();
                if (existing) {{
                    resolve(existing);
                    return;
                }}
                const script = document.createElement("script");
                script.src = segmentitScript;
                script.async = true;
                script.onload = () => resolve(initSegmenter());
                script.onerror = () => resolve(null);
                document.head.appendChild(script);
            }});

        const ensureSegmenter = (term) => {{
            if (!shouldSegment(term)) {{
                return null;
            }}
            if (segmenter) {{
                return Promise.resolve(segmenter);
            }}
            if (!segmenterPromise) {{
                segmenterPromise = loadSegmenter().then((loaded) => {{
                    segmenter = loaded;
                    return loaded;
                }});
            }}
            return segmenterPromise;
        }};

        const segmentText = (text) => {{
            if (!segmenter) {{
                return [];
            }}
            try {{
                return segmenter
                    .doSegment(text)
                    .map((token) => token.w || token.word || "")
                    .filter((token) => token && token.trim());
            }} catch (error) {{
                return [];
            }}
        }};

        const normalizeQuery = (term) => {{
            const trimmed = term.trim();
            if (!trimmed) {{
                return {{ primary: "", phrase: "", raw: "", tokens: [] }};
            }}
            const hasSpace = /\\s/.test(trimmed);
            let tokens = [];
            if (shouldSegment(trimmed) && segmenter) {{
                tokens = segmentText(trimmed);
            }}
            const longTokens = tokens.filter((token) => token.length > 1);
            const queryTokens = longTokens.length ? longTokens : tokens;
            const tokenQuery = queryTokens.length
                ? queryTokens.map((token) => (token.length > 1 ? `\\"${{token}}\\"` : token)).join(" ")
                : "";
            if (hasCJK(trimmed) && !hasSpace) {{
                const spaced = trimmed.split("").join(" ");
                return {{ primary: tokenQuery || trimmed, phrase: `\\"${{spaced}}\\"`, raw: trimmed, tokens: queryTokens }};
            }}
            return {{ primary: tokenQuery || trimmed, phrase: "", raw: trimmed, tokens: queryTokens }};
        }};

        const clearResults = () => {{
            resultsEl.innerHTML = "";
            metaEl.textContent = "";
            moreButton.style.display = "none";
            lastResults = [];
            lastRendered = 0;
        }};

        const getData = async (wrapper) => {{
            if (wrapper.data) {{
                return wrapper.data;
            }}
            const cacheKey = wrapper.result.url || wrapper.result.id;
            if (cacheKey && dataCache.has(cacheKey)) {{
                wrapper.data = dataCache.get(cacheKey);
                return wrapper.data;
            }}
            const data = await wrapper.result.data();
            wrapper.data = data;
            if (cacheKey) {{
                dataCache.set(cacheKey, data);
            }}
            return data;
        }};

        const renderBatch = async () => {{
            const slice = lastResults.slice(lastRendered, lastRendered + pageSize);
            const data = await Promise.all(slice.map((item) => getData(item)));
            data.forEach((item) => {{
                const li = document.createElement("li");
                li.className = "search-result";
                const title = item.meta?.title || item.meta?.page_title || item.title || item.url || "未命名";
                const thumb = item.meta && item.meta.image
                    ? `<div class=\\"search-result-thumb\\"><img src=\\"${{item.meta.image}}\\" alt=\\"${{title}}\\"></div>`
                    : "";
                li.innerHTML = `${{thumb}}<div class=\\"search-result-body\\">
                    <p class=\\"search-result-title\\"><a href=\\"${{item.url}}\\" target=\\"_blank\\" rel=\\"noopener noreferrer\\">${{title}}</a></p>
                    <p class=\\"search-result-excerpt\\">${{item.excerpt}}</p>
                </div>`;
                resultsEl.appendChild(li);
            }});
            lastRendered += slice.length;
            if (lastRendered >= lastResults.length) {{
                moreButton.style.display = "none";
            }} else {{
                moreButton.style.display = "inline-flex";
            }}
        }};

        const matchesStrict = (content, raw, tokens) => {{
            if (!content) {{
                return false;
            }}
            if (raw && content.includes(raw)) {{
                return true;
            }}
            if (tokens && tokens.length) {{
                return tokens.every((token) => token && content.includes(token));
            }}
            return false;
        }};

        const filterResults = async (results, raw, tokens) => {{
            const shouldFilter = hasCJK(raw) && raw.length >= minCjkLength;
            if (!shouldFilter) {{
                return {{ results, filtered: false, truncated: false, strict: false }};
            }}
            const filtered = [];
            let scanned = 0;
            for (const wrapper of results) {{
                if (scanned >= maxScan) {{
                    break;
                }}
                const data = await getData(wrapper);
                scanned += 1;
                const content = `${{data.title || ""}} ${{data.excerpt || ""}} ${{data.content || ""}}`;
                if (matchesStrict(content, raw, tokens)) {{
                    filtered.push({{ result: wrapper.result, data }});
                }}
            }}
            if (!filtered.length) {{
                return {{ results, filtered: false, truncated: scanned < results.length, strict: true }};
            }}
            return {{ results: filtered, filtered: true, truncated: scanned < results.length, strict: true }};
        }};

        const searchAndRender = async (term) => {{
            if (!pagefind) {{
                return;
            }}
            const token = ++lastSearchToken;
            const hadSegmenter = !!segmenter;
            const trimmed = term.trim();
            if (!trimmed) {{
                clearResults();
                return;
            }}
            if (shouldSegment(trimmed) && !segmenter) {{
                metaEl.textContent = "正在加载中文分词库…";
                const pending = ensureSegmenter(trimmed);
                if (pending) {{
                    pending.then((loaded) => {{
                        if (!loaded) {{
                            metaEl.textContent = "中文分词库加载失败，使用普通搜索。";
                        }}
                        if (token !== lastSearchToken) {{
                            return;
                        }}
                        if (input.value.trim() === trimmed) {{
                            searchAndRender(trimmed);
                        }}
                    }});
                }}
                return;
            }}

            const segmentPromise = ensureSegmenter(trimmed);
            const {{ primary, phrase, raw, tokens }} = normalizeQuery(trimmed);
            if (!primary) {{
                clearResults();
                return;
            }}

            const candidates = [];
            if (primary) {{
                candidates.push(primary);
            }}
            if (phrase) {{
                candidates.push(phrase);
            }}
            if (raw && raw !== primary && raw !== phrase) {{
                candidates.push(raw);
            }}

            let result = await pagefind.search(primary);
            let usedQuery = primary;

            for (const candidate of candidates) {{
                const candidateResult = await pagefind.search(candidate);
                if (!candidateResult.results.length) {{
                    continue;
                }}
                if (!result.results.length || candidateResult.results.length < result.results.length) {{
                    result = candidateResult;
                    usedQuery = candidate;
                }}
            }}

            lastRawResults = result.results.map((item) => ({{ result: item }}));
            lastResults = lastRawResults;
            lastRendered = 0;
            resultsEl.innerHTML = "";

            if (!lastResults.length) {{
                metaEl.textContent = `没有找到与“${{term}}”相关的结果`;
                moreButton.style.display = "none";
                return;
            }}

            const usedHint = usedQuery && usedQuery !== raw ? "（已自动优化匹配）" : "";
            metaEl.textContent = `找到 ${{lastResults.length}} 个与“${{term}}”相关的结果${{usedHint}}`;
            await renderBatch();

            const shouldFilter = hasCJK(raw) && raw.length >= minCjkLength;
            if (shouldFilter) {{
                metaEl.textContent += "（正在精确匹配…）";
                setTimeout(async () => {{
                    if (token !== lastSearchToken) {{
                        return;
                    }}
                    const filtered = await filterResults(lastRawResults, raw, tokens);
                    if (token !== lastSearchToken) {{
                        return;
                    }}
                    if (filtered.filtered) {{
                        lastResults = filtered.results;
                        lastRendered = 0;
                        resultsEl.innerHTML = "";
                        const filterHint = "（已按中文分词筛选）";
                        const truncateHint = filtered.truncated ? "（已限制精确筛选范围）" : "";
                        metaEl.textContent = `找到 ${{lastResults.length}} 个与“${{term}}”相关的结果${{usedHint}}${{filterHint}}${{truncateHint}}`;
                        await renderBatch();
                    }} else if (filtered.strict) {{
                        const truncateHint = filtered.truncated ? "（已限制精确筛选范围）" : "";
                        metaEl.textContent = `找到 ${{lastResults.length}} 个与“${{term}}”相关的结果${{usedHint}}（未找到更精确结果，显示相关结果）${{truncateHint}}`;
                    }}
                }}, 0);
            }}

            if (segmentPromise && !hadSegmenter) {{
                segmentPromise.then((loaded) => {{
                    if (!loaded) {{
                        return;
                    }}
                    if (token !== lastSearchToken) {{
                        return;
                    }}
                    if (input.value.trim() === term.trim()) {{
                        searchAndRender(term);
                    }}
                }});
            }}
        }};

        const debounce = (fn, delay = 500) => {{
            let timer;
            return (...args) => {{
                clearTimeout(timer);
                timer = setTimeout(() => fn(...args), delay);
            }};
        }};

        const init = async () => {{
            pagefind = await import(`${{basePath}}pagefind/pagefind.js`);
            await pagefind.options({{
                baseUrl: basePath,
                bundlePath: `${{basePath}}pagefind/`,
            }});
            await pagefind.init();

            input.addEventListener("input", debounce((event) => {{
                lastQuery = event.target.value;
                searchAndRender(lastQuery);
            }}));
            moreButton.addEventListener("click", renderBatch);
        }};

        init();
    </script>

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
