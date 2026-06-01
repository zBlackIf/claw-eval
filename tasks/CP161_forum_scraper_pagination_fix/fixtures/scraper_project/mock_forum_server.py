"""Mock HTTP server that simulates a Discuz!-based forum for testing.
Provides forum pages with pagination in the URL pattern: forum-25-{page}.html
Encoding: GBK (as typical for Chinese Discuz forums).
"""
import http.server
import re


TOTAL_PAGES = 50
POSTS_PER_PAGE = 5


def generate_forum_page(page_num: int) -> bytes:
    """Generate a mock forum page with thread listings."""
    posts_html = ""
    for i in range(POSTS_PER_PAGE):
        thread_id = (page_num - 1) * POSTS_PER_PAGE + i + 1
        posts_html += f'''
<tbody id="normalthread_{thread_id}">
<tr>
<td class="icn"><a href="thread-{thread_id}-1-1.html"><img src="folder.gif"/></a></td>
<th><a href="thread-{thread_id}-1-1.html" class="s xst">Test Thread Title {thread_id} on Page {page_num}</a></th>
<td class="by"><cite>user{thread_id % 100}</cite><em>2026-5-{10 + (thread_id % 20)}</em></td>
<td class="num"><a href="thread-{thread_id}-1-1.html" class="xi2">{thread_id * 3}</a></td>
<td class="by"><cite>replier{thread_id % 50}</cite><em>2026-5-{15 + (thread_id % 10)}</em></td>
</tr>
</tbody>'''

    # Pagination: show links to pages with max page visible
    page_links = ""
    visible_pages = [1, 2, 3, page_num - 1, page_num, page_num + 1, TOTAL_PAGES - 1, TOTAL_PAGES]
    visible_pages = sorted(set(p for p in visible_pages if 1 <= p <= TOTAL_PAGES))
    for p in visible_pages:
        if p == page_num:
            page_links += f'<strong>{p}</strong> '
        else:
            page_links += f'<a href="forum-25-{p}.html">{p}</a> '

    html = f'''<html>
<head><meta charset="gbk"><title>Test Forum Section - Page {page_num}</title></head>
<body>
<div id="wrapper">
<h1>Test Forum - Section 25</h1>
<table id="threadlisttableid" class="datatable">
{posts_html}
</table>
<div class="pg">
{page_links}
<span class="label">... <a href="forum-25-{TOTAL_PAGES}.html">{TOTAL_PAGES}</a></span>
</div>
</div>
</body>
</html>'''
    return html.encode('gbk', errors='replace')


class ForumHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Match forum-25-{page}.html
        match = re.search(r'forum-25-(\d+)\.html', self.path)
        if match:
            page = int(match.group(1))
            if 1 <= page <= TOTAL_PAGES:
                content = generate_forum_page(page)
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=gbk')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not Found')

    def log_message(self, format, *args):
        pass  # Suppress output


def run_server(port=18923):
    server = http.server.HTTPServer(('127.0.0.1', port), ForumHandler)
    print(f"Mock forum server running on http://127.0.0.1:{port}")
    print(f"Test URL: http://127.0.0.1:{port}/forum/forum-25-1.html")
    server.serve_forever()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 18923))
    run_server(port=port)
