"""Tests for md_render converter"""
import pytest
from md_render import md2html, MarkdownRenderer


class TestMd2Html:
    """Tests for md2html function"""
    
    def test_basic_conversion(self):
        md = "# Hello World"
        html = md2html(md, title="Test")
        
        assert "<h1>" in html
        assert "Hello World" in html
        assert "<html" in html
        assert "</html>" in html
    
    def test_table_conversion(self):
        md = """
| Column A | Column B |
|----------|----------|
| Value 1  | Value 2  |
"""
        html = md2html(md)
        
        assert "<table>" in html
        assert "<th>" in html
        assert "Column A" in html
        assert "Value 1" in html
    
    def test_code_block(self):
        md = """
```python
def hello():
    print("world")
```
"""
        html = md2html(md)
        
        assert "<code" in html
        assert "hello" in html
    
    def test_custom_title(self):
        md = "# Content"
        html = md2html(md, title="Custom Title")
        
        assert "<title>Custom Title</title>" in html
    
    def test_include_toc(self):
        md = """
# Heading 1
## Heading 2
### Heading 3
"""
        html = md2html(md, include_toc=True)
        
        assert 'class="toc"' in html


class TestMarkdownRenderer:
    """Tests for MarkdownRenderer class"""
    
    def test_render_fragment(self):
        renderer = MarkdownRenderer()
        html = renderer.render_fragment("**bold**")
        
        assert "<strong>bold</strong>" in html
        assert "<html" not in html
    
    def test_render_with_footnotes(self):
        renderer = MarkdownRenderer()
        html = renderer.render(
            "Content",
            footnotes="<p>Footnote 1</p>"
        )
        
        assert 'class="footnotes"' in html
        assert "Footnote 1" in html
