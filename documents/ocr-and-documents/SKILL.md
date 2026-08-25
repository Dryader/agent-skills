---
name: ocr-and-documents
description: "Extract text from PDFs/scans (pymupdf, marker-pdf)."
tags: [PDF, Documents, Research, Arxiv, Text-Extraction, OCR]
related_skills: [powerpoint]
triggers:
  - extracting text from PDFs or scans
  - OCR task
  - parsing scanned documents

---

# PDF & Document Extraction

For DOCX: use `python-docx` (parses actual document structure, far better than OCR).
For PPTX: see the `powerpoint` skill (uses `python-pptx` with full slide/notes support).
This skill covers **PDFs and scanned documents**.

## Step 1: Remote URL Available?

If the document has a URL, **always try `web_extract` first**:

```
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])
web_extract(urls=["https://example.com/report.pdf"])
```

This handles PDF-to-markdown conversion via Firecrawl with no local dependencies.

Only use local extraction when: the file is local, web_extract fails, or you need batch processing.

## Step 2: Choose Local Extractor

| Feature | pymupdf (~25MB) | marker-pdf (~3-5GB) |
|---------|-----------------|---------------------|
| **Text-based PDF** | ✅ | ✅ |
| **Scanned PDF (OCR)** | ❌ | ✅ (90+ languages) |
| **Tables** | ✅ (basic) | ✅ (high accuracy) |
| **Equations / LaTeX** | ❌ | ✅ |
| **Code blocks** | ❌ | ✅ |
| **Forms** | ❌ | ✅ |
| **Headers/footers removal** | ❌ | ✅ |
| **Reading order detection** | ❌ | ✅ |
| **Images extraction** | ✅ (embedded) | ✅ (with context) |
| **Images → text (OCR)** | ❌ | ✅ |
| **EPUB** | ✅ | ✅ |
| **Markdown output** | ✅ (via pymupdf4llm) | ✅ (native, higher quality) |
| **Install size** | ~25MB | ~3-5GB (PyTorch + models) |
| **Speed** | Instant | ~1-14s/page (CPU), ~0.2s/page (GPU) |

**Decision**: Use pymupdf unless you need OCR, equations, forms, or complex layout analysis.

If the user needs marker capabilities but the system lacks ~5GB free disk:
> "This document needs OCR/advanced extraction (marker-pdf), which requires ~5GB for PyTorch and models. Your system has [X]GB free. Options: free up space, provide a URL so I can use web_extract, or I can try pymupdf which works for text-based PDFs but not scanned documents or equations."

---

## pymupdf (lightweight)

```bash
pip install pymupdf pymupdf4llm pandas tabulate
```

**Via helper script**:
```bash
python scripts/extract_pymupdf.py document.pdf              # Plain text
python scripts/extract_pymupdf.py document.pdf --markdown    # Markdown
python scripts/extract_pymupdf.py document.pdf --tables      # Tables
python scripts/extract_pymupdf.py document.pdf --images out/ # Extract images
python scripts/extract_pymupdf.py document.pdf --metadata    # Title, author, pages
python scripts/extract_pymupdf.py document.pdf --pages 0-4   # Specific pages
```

**Inline**:
```bash
python3 -c "
import pymupdf
doc = pymupdf.open('document.pdf')
for page in doc:
    print(page.get_text())
"
```

---

## marker-pdf (high-quality OCR)

```bash
# Check disk space first
python scripts/extract_marker.py --check

pip install marker-pdf
```

**Via helper script**:
```bash
python scripts/extract_marker.py document.pdf                # Markdown
python scripts/extract_marker.py document.pdf --json         # JSON with metadata
python scripts/extract_marker.py document.pdf --output_dir out/  # Save images
python scripts/extract_marker.py scanned.pdf                 # Scanned PDF (OCR)
python scripts/extract_marker.py document.pdf --use_llm      # LLM-boosted accuracy
```

**CLI** (installed with marker-pdf):
```bash
marker_single document.pdf --output_dir ./output
marker /path/to/folder --workers 4    # Batch
```

---

## Arxiv Papers

```
# Abstract only (fast)
web_extract(urls=["https://arxiv.org/abs/2402.03300"])

# Full paper
web_extract(urls=["https://arxiv.org/pdf/2402.03300"])

# Search
web_search(query="arxiv GRPO reinforcement learning 2026")
```

## Split, Merge & Search

pymupdf handles these natively — use `execute_code` or inline Python:

```python
# Split: extract pages 1-5 to a new PDF
import pymupdf
doc = pymupdf.open("report.pdf")
new = pymupdf.open()
for i in range(5):
    new.insert_pdf(doc, from_page=i, to_page=i)
new.save("pages_1-5.pdf")
```

```python
# Merge multiple PDFs
import pymupdf
result = pymupdf.open()
for path in ["a.pdf", "b.pdf", "c.pdf"]:
    result.insert_pdf(pymupdf.open(path))
result.save("merged.pdf")
```

```python
# Search for text across all pages
import pymupdf
doc = pymupdf.open("report.pdf")
for i, page in enumerate(doc):
    results = page.search_for("revenue")
    if results:
        print(f"Page {i+1}: {len(results)} match(es)")
        print(page.get_text("text"))
```

No extra dependencies needed — pymupdf covers split, merge, search, and text extraction in one package.

---

## Large Document Analysis (50+ pages)

For long PDFs (prospectuses, annual reports, research papers), do NOT extract all pages at once — it floods context. Instead:

1. **Get metadata + page count** first (instant).
2. **Extract the table of contents** (usually pages 1-10) to identify section locations.
3. **Extract targeted page ranges** for each important section, saving each to a separate temp file.
4. **Use `search_files` on extracted text** to find specific terms, then `read_file` with offset/limit around matches.

Example workflow for a 400-page prospectus:
```python
# Step 1: metadata + TOC
doc = pymupdf.open('prospectus.pdf')
print(f"Pages: {len(doc)}")
# Extract first 10 pages for TOC
text = "".join(doc[i].get_text() for i in range(10))

# Step 2: extract key sections by page range (from TOC)
for section, (start, end) in [("summary", (13, 50)), ("financials", (50, 60)), ("risk_factors", (221, 260))]:
    text = "".join(f"\n=== PAGE {i+1} ===\n" + doc[i].get_text() for i in range(start-1, end))
    with open(f'/tmp/{section}.txt', 'w') as f:
        f.write(text)

# Step 3: search within extracted sections
# Use search_files tool on /tmp/ files, then read_file with offset around matches
```

**Document-type extraction priorities:**
- **Prospectuses/SEDAR filings**: TOC → Prospectus Summary → The Offering → Financial Statements → Risk Factors → Use of Proceeds → Material Indebtedness
- **Annual reports**: TOC → MD&A → Financial Statements → Notes
- **Research papers**: Abstract → Introduction → Results → Discussion

**Pitfall**: Prospectus page numbers (printed on the page) are offset from PDF page indices. The TOC says "Risk Factors ... 222" but that's the printed page number; the PDF page index is typically different. Search for the section heading text in the extracted TOC to find the real offset, or scan the first page of each section to calibrate.

## Install Pitfalls

- If `pip` / `pip3` are not available (common in WSL/minimal installs), use `uv venv`:
  ```bash
  uv venv /tmp/pdfvenv --python python3
  source /tmp/pdfvenv/bin/activate
  uv pip install pymupdf pymupdf4llm pandas tabulate
  ```
  Then run extractions with `/tmp/pdfvenv/bin/python3 -c "..."`.

## Notes

- `web_extract` is always first choice for URLs
- pymupdf is the safe default — instant, no models, works everywhere
- marker-pdf is for OCR, scanned docs, equations, complex layouts — install only when needed
- Both helper scripts accept `--help` for full usage
- marker-pdf downloads ~2.5GB of models to `~/.cache/huggingface/` on first use
- For Word docs: `pip install python-docx` (better than OCR — parses actual structure)
- For PowerPoint: see the `powerpoint` skill (uses python-pptx)
