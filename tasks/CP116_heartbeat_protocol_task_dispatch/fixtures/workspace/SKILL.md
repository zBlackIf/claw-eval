# Book Rating Skill v3.5

## Rating System (3-tier)

| Level | Label | Criteria |
|-------|-------|----------|
| 1 | 过时 (Outdated) | Published > 15 years ago AND core technology is obsolete (e.g., specific framework versions no longer maintained) |
| 2 | 部分有效 (Partially Useful) | Some content outdated but core concepts/principles still valuable |
| 3 | 经典 (Classic) | Timeless principles, still actively recommended, high community rating (>= 8.5) |

## Rating Rules

1. Books published within the last 5 years default to Level 2 unless they meet classic criteria
2. Books with Douban rating >= 9.0 AND covering fundamental CS concepts are Level 3 regardless of age
3. Books about specific framework versions (e.g., "Rails 3", "Angular 1.x") published > 8 years ago are Level 1
4. Books about algorithms, data structures, OS principles, compiler theory are Level 3 if rating >= 8.0
5. If publication year is missing, assume current year minus 10

## Output Format (Hexo Markdown)

```markdown
---
title: {book_title}
tags:
  - 读书
  - 技术图书
  - {level_label_chinese}
  - {primary_topic}
categories: 读书
date: {processing_date}
rating_level: {1|2|3}
---

{book_title_wrapped} 是一本技术图书，豆瓣评分{douban_rating}。出版于{pub_year}年。
本书评级为{level}级（{level_label}），{rating_reason}。

## 有价值的章节

{valuable_chapters_list}

## 清理建议

{cleanup_suggestion}
```

## Processing Rules

- Process books in queue order (first to last)
- Each book MUST produce exactly one output .md file
- Filename: `book-{slugified_title}.md` (see HEARTBEAT.md for slug rules)
- Do NOT skip any book in the queue
- Do NOT modify books_queue.json
