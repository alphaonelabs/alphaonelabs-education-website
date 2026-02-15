from django.test import TestCase

from web.templatetags.markdown_filters import markdown


class MarkdownFilterSanitizationTests(TestCase):
    """Tests to verify that the markdown template filter sanitizes HTML
    to prevent XSS while preserving valid markdown formatting."""

    # --- XSS payload tests ---

    def test_script_tag_is_stripped(self):
        """Script tags must be completely removed."""
        result = markdown('<script>alert("XSS")</script>')
        self.assertNotIn("<script", result)
        self.assertNotIn("</script>", result)
        # Content remains as text, which is safe
        # self.assertNotIn("alert", result)

    def test_img_onerror_is_stripped(self):
        """Event handler attributes on img tags must be removed."""
        result = markdown('<img src="x" onerror="alert(1)">')
        self.assertNotIn("onerror", result)
        # self.assertNotIn("alert", result)

    def test_javascript_protocol_in_link_is_stripped(self):
        """javascript: protocol in href must be removed or neutralized."""
        result = markdown('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", result)

    def test_iframe_is_stripped(self):
        """iframe tags must be completely removed."""
        result = markdown('<iframe src="https://evil.com"></iframe>')
        self.assertNotIn("<iframe", result)
        self.assertNotIn("</iframe>", result)

    def test_onmouseover_event_is_stripped(self):
        """Inline event handlers must be removed."""
        result = markdown('<div onmouseover="alert(1)">hover me</div>')
        self.assertNotIn("onmouseover", result)
        # self.assertNotIn("alert", result)

    def test_style_tag_is_stripped(self):
        """Style tags must be removed."""
        result = markdown("<style>body{display:none}</style>")
        self.assertNotIn("<style", result)

    def test_nested_script_in_markdown(self):
        """Script tags embedded within markdown content must be stripped."""
        text = '# Hello\n\nSome text <script>alert("XSS")</script> more text'
        result = markdown(text)
        self.assertNotIn("<script", result)
        self.assertIn("Hello", result)
        self.assertIn("Some text", result)

    # --- Valid markdown preservation tests ---

    def test_heading_renders(self):
        """Markdown headings should render as HTML heading tags."""
        result = markdown("# Heading 1")
        self.assertIn("<h1>", result)
        self.assertIn("Heading 1", result)

    def test_bold_renders(self):
        """Markdown bold syntax should render as strong tags."""
        result = markdown("**bold text**")
        self.assertIn("<strong>", result)
        self.assertIn("bold text", result)

    def test_italic_renders(self):
        """Markdown italic syntax should render as em tags."""
        result = markdown("*italic text*")
        self.assertIn("<em>", result)
        self.assertIn("italic text", result)

    def test_link_renders(self):
        """Markdown links should render as anchor tags with href."""
        result = markdown("[Example](https://example.com)")
        self.assertIn("<a", result)
        self.assertIn("https://example.com", result)
        self.assertIn("Example", result)

    def test_unordered_list_renders(self):
        """Markdown unordered lists should render as ul/li tags."""
        result = markdown("- item 1\n- item 2")
        self.assertIn("<ul>", result)
        self.assertIn("<li>", result)
        self.assertIn("item 1", result)

    def test_code_block_renders(self):
        """Markdown code blocks should render as pre/code tags."""
        result = markdown("```\nprint('hello')\n```")
        self.assertIn("<code>", result)
        self.assertIn("print", result)

    def test_inline_code_renders(self):
        """Markdown inline code should render as code tags."""
        result = markdown("`inline code`")
        self.assertIn("<code>", result)
        self.assertIn("inline code", result)

    def test_blockquote_renders(self):
        """Markdown blockquotes should render as blockquote tags."""
        result = markdown("> This is a quote")
        self.assertIn("<blockquote>", result)
        self.assertIn("This is a quote", result)

    def test_empty_string(self):
        """Empty string input should not raise an error."""
        result = markdown("")
        self.assertIsNotNone(result)

    def test_plain_text_passthrough(self):
        """Plain text without markdown should pass through unchanged."""
        result = markdown("Just plain text")
        self.assertIn("Just plain text", result)
