import os

if __name__ == "__main__":
    articles = os.listdir("article")
    try:
        articles.remove(".DS_Store")
    except:
        pass
    with open("article/index.html", "w", encoding="utf-8") as f:
        f.write("<meta charset=\"UTF-8\">\n")
        for article in articles:
            f.write(f"<p><a href=\"{article}\">{article}</a></p>\n")

    answers = os.listdir("answer")
    try:
        answers.remove(".DS_Store")
    except:
        pass
    with open("answer/index.html", "w", encoding="utf-8") as f:
        f.write("<meta charset=\"UTF-8\">\n")
        for answer in answers:
            f.write(f"<p><a href=\"{answer}\">{answer}</a></p>\n")

    pins = os.listdir("pin")
    try:
        articles.remove(".DS_Store")
    except:
        pass
    with open("pin/index.html", "w", encoding="utf-8") as f:
        f.write("<meta charset=\"UTF-8\">\n")
        for pin in pins:
            f.write(f"<p><a href=\"{pin}\">{pin}</a></p>\n")


    questions = os.listdir("question")
    try:
        questions.remove(".DS_Store")
    except:
        pass
    with open("question/index.html", "w", encoding="utf-8") as f:
        f.write("<meta charset=\"UTF-8\">\n")
        for question in questions:
            f.write(f"<p><a href=\"{question}\">{question}</a></p>\n")

    with open("index.html", "w", encoding="utf-8") as f:
        f.write("<meta charset=\"UTF-8\">\n")
        f.write("<p><a href=\"answer/index.html\">答案</a></p>\n")
        f.write("<p><a href=\"article/index.html\">文章</a></p>\n")
        f.write("<p><a href=\"pin/index.html\">想法</a></p>\n")
        f.write("<p><a href=\"question/index.html\">提问</a></p>\n")
