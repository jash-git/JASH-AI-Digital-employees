# Full-Text Extraction from Web Sources

Validated recipe for pulling the complete text of an article/essay/document when
`web_extract` (search-only DuckDuckGo backend) and Google/Bing scraping both fail.
Worked example: 陳思宏〈泳褲〉full essay, extracted from womany.net.

## Worked example: 陳思宏〈泳褲〉全文

Goal: full essay text; most search hits were news articles *about* the controversy,
not the essay itself.

- `web_extract` (DuckDuckGo backend) → empty on real URLs. Skipped it.
- Google/Bing via curl → JS interstitials / unparseable redirects. Skipped them.
- Fetched candidate article pages with the recipe above; **womany.net**
  (`/read/article/…`) returned HTTP 200 + ~67 KB of real essay text.
- Located the body by grepping for in-body phrases ("你的泳褲、泳衣，長什麼樣子？",
  "女生怕胸小，男生也怕雞小啊"), extracted start→end, verified it ended at the
  closing line "我們都放過彼此吧。" (matching the LTN summary's described ending).

## Key commands

Realistic UA + headers (many TW sites return 000/403 without a real UA):
```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
curl -sL -A "$UA" -H "Accept-Language: zh-TW,zh;q=0.9" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -o /tmp/page.html --max-time 40 "$URL"
```

Strip tags → collapse whitespace → inspect body:
```bash
sed 's/<[^>]*>//g' /tmp/page.html | tr -s ' \t\r' '   ' > /tmp/page.txt
wc -c /tmp/page.txt
grep -o '.\{0,60\}KEYWORD.\{0,300\}' /tmp/page.txt | head
```

Extract start→end with Python (find body by distinctive phrase, stop at footer):
```python
text=open('/tmp/page.txt',encoding='utf-8',errors='ignore').read()
start=text.find('你的泳褲、泳衣，長什麼樣子？')   # in-body anchor
end  =text.find('延伸閱讀：')                     # natural end boundary
print(text[start:end].strip())
```

## Sanity checks before delivering full text

- Confirm the source actually contains the essay (grep for an in-body quote), not
  just a title mention.
- Verify the end boundary is the natural conclusion, not mid-sentence or a footer.
- Note provenance: which page held the full text and when you fetched it.
