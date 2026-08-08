from app.scrapers.js_detect import is_useful_html, looks_like_js_shell


def test_detects_js_shell_markers():
    html = "<html><body><p>Please enable JavaScript to view this site.</p></body></html>"
    assert looks_like_js_shell(html)
    assert not is_useful_html(html)


def test_detects_spa_empty_root():
    html = """
    <html><head><script src="/app.js"></script><script src="/chunk.js"></script></head>
    <body><div id="root"></div><noscript>Enable JS</noscript></body></html>
    """
    assert looks_like_js_shell(html)


def test_accepts_rich_static_html():
    html = """
    <html><body>
    <h1>Acme Web Design Agency</h1>
    <p>We build websites in London. Contact us at hello@acme.co.uk or +44 20 7946 0958.</p>
    <p>Our studio has helped hundreds of businesses grow online with modern design.</p>
  """ + ("<p>More content about services.</p>" * 20) + """
    </body></html>
    """
    assert not looks_like_js_shell(html)
    assert is_useful_html(html)


def test_detects_next_data_shell():
    html = "<html><body><script>window.__NEXT_DATA__={}</script><div id='__next'></div></body></html>"
    assert looks_like_js_shell(html)
