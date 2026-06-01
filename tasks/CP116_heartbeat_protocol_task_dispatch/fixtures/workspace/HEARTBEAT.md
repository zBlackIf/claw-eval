# HEARTBEAT.md

## Status: PENDING

## Task
Process the book queue in `books_queue.json`. For each entry:
1. Read the book info
2. Apply the rating rules from SKILL.md
3. Write the rating result as a Hexo-compatible Markdown file to `output/`

## Filename Convention
- Chinese book titles: pinyin with hyphens between each syllable, prefixed with `book-`
- English book titles: lowercase words with hyphens, prefixed with `book-`
- Example: "GNU Emacs Lisp 编程入门" -> `book-gnu-emacs-lisp-bian-cheng-ru-men.md`

## Completion Signal
When all books are processed, update this file:
- Change `Status: PENDING` to `Status: DONE`
- Add a `## Results` section listing each book processed with its rating level
