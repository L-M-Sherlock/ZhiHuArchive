import json
from pathlib import Path
from datetime import datetime

# Collect all articles
articles = []
for file in Path("article").glob("*.json"):
    with open(file, "r") as f:
        data = json.load(f)
        data["file_stem"] = file.stem
        articles.append(data)

# Collect all answers
answers = []
for file in Path("answer").glob("*.json"):
    with open(file, "r") as f:
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
<html>
<head>
    <meta charset="UTF-8">
    <title>Content Directory</title>
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
    <h1>Content Directory</h1>
    
    <div class="tabs">
        <button class="tab-button active" onclick="openTab(event, 'articles-tab')">Articles ({len(articles)})</button>
        <button class="tab-button" onclick="openTab(event, 'answers-tab')">Answers ({len(answers)})</button>
    </div>

    <div id="articles-tab" class="tab-content active">
        <h2>Articles</h2>
"""
)

# Add articles
for article in articles:
    is_censored = article.get("censored", False)
    censored_class = "censored" if is_censored else ""
    censored_text = " (censored)" if is_censored else ""
    html_content += f"""
        <div class="item">
            <a href="./{article['file_stem']}.html" class="{censored_class}">{article['title']}{censored_text}</a>
            <span class="votes">({article['voteup_count']} votes)</span>
            <span class="created_time">({datetime.fromtimestamp(article['created']).strftime('%Y-%m-%d')})</span>
        </div>
"""

html_content += """
    </div>
    
    <div id="answers-tab" class="tab-content">
        <h2>Answers</h2>
"""

# Add answers
for answer in answers:
    question_title = (
        answer["question"]["title"]
        if "question" in answer and "title" in answer["question"]
        else "Untitled"
    )
    is_censored = answer.get("censored", False)
    censored_class = "censored" if is_censored else ""
    censored_text = " (censored)" if is_censored else ""

    html_content += f"""
        <div class="item">
            <a href="./{answer['file_stem']}.html" class="{censored_class}">{question_title}{censored_text}</a>
            <span class="votes">({answer['voteup_count']} votes)</span>
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
