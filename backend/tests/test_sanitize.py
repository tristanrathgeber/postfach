from postfach.sanitize import sanitize_mail_html


def test_scripts_styles_and_handlers_removed():
    html = (
        "<div onclick=\"evil()\"><script>alert(1)</script>"
        "<style>body{background:red}</style><p>Hallo</p></div>"
    )
    result = sanitize_mail_html(html)
    assert "Hallo" in result.blocked
    assert "script" not in result.blocked.lower()
    assert "onclick" not in result.blocked
    assert "background:red" not in result.blocked


def test_javascript_urls_stripped():
    result = sanitize_mail_html('<a href="javascript:alert(1)">Klick</a>')
    assert "javascript:" not in result.blocked


def test_remote_images_blocked_but_recoverable():
    html = '<p>Angebot</p><img src="https://tracker.example/pixel.png" alt="x">'
    result = sanitize_mail_html(html)
    assert "tracker.example" not in result.blocked  # Quelle komplett raus
    assert result.had_remote_images is True
    # Variante mit Bildern behält die Quelle
    assert 'src="https://tracker.example/pixel.png"' in result.with_images


def test_image_blocking_survives_bypass_attempts():
    # Regex-Bypässe aus dem Security-Review: alt=">" und protokoll-relative URL
    tricky = '<img alt=">" src="https://track.evil/o.gif?u=1">'
    result = sanitize_mail_html(tricky)
    assert "track.evil" not in result.blocked
    assert result.had_remote_images is True

    protocol_relative = '<img src="//track.evil/o.gif">'
    result2 = sanitize_mail_html(protocol_relative)
    assert "track.evil" not in result2.blocked
    assert result2.had_remote_images is True


def test_cid_inline_images_survive_blocking():
    result = sanitize_mail_html('<img src="cid:logo123" alt="Logo">')
    assert 'src="cid:logo123"' in result.blocked
    assert result.had_remote_images is False


def test_no_remote_images_means_no_image_variant_needed():
    result = sanitize_mail_html("<p>Nur Text</p>")
    assert result.had_remote_images is False


def test_links_get_target_blank_noopener():
    result = sanitize_mail_html('<a href="https://example.de/x">Link</a>')
    assert 'target="_blank"' in result.blocked
    assert "noopener" in result.blocked
    assert 'href="https://example.de/x"' in result.blocked
