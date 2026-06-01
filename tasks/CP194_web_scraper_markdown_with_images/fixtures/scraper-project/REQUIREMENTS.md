# Web Article Scraper - Requirements

## Overview
Build a Python script that converts local HTML article files into well-structured Markdown,
downloads/copies embedded images, and organizes everything into an Obsidian-compatible vault structure.

## Output Directory Structure

```
output/
├── YYYYMMDD_Source_ArticleTitle.md
└── images/
    └── YYYYMMDD_Source_ShortHash/
        ├── img_1.png
        ├── img_2.jpg
        └── ...
```

## Naming Convention
- Markdown files: `{date}_{source}_{title}.md`
  - date: from article metadata (publish_time), format YYYYMMDD
  - source: extracted from `rich_media_meta_nickname`, Chinese OK
  - title: from `activity-name` or `<title>`, truncated to 30 chars if needed
- Image folders: `{date}_{source}_{first8chars_of_md5(article_title)}/`

## Image Handling
- Extract image URLs from `data-src` attribute (fallback to `src`)
- Since we're working with local HTML files, simulate image download by creating
  placeholder files (1x1 pixel PNG) with the correct filenames
- In the output Markdown, replace image references with Obsidian-compatible relative paths:
  `![alt](images/{folder_name}/img_N.ext)`
- Images must appear in the same position as in the original HTML

## Markdown Conversion Requirements
- Preserve heading hierarchy (h2 → ##, h3 → ###, etc.)
- Convert lists (ul/ol) properly
- Preserve code blocks with language hints if available
- Convert tables to Markdown tables
- Preserve blockquotes
- Add YAML frontmatter with: title, source, date, url (empty for local files)

## Verification
- After processing, the script should output a JSON summary to stdout:
  ```json
  {
    "articles_processed": N,
    "total_images": N,
    "output_files": ["path1.md", "path2.md"],
    "errors": []
  }
  ```
