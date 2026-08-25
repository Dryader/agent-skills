---
name: python-docx
description: Read, edit, and create .docx Word documents programmatically with python-docx. Covers text manipulation, formatting preservation, hyperlink handling, and document restructuring.
tags: [docx, word, documents, python-docx, office, resume, templates]
triggers:
  - user asks to read, edit, modify, or create a .docx file
  - user mentions Word documents, resume templates, or document restructuring
  - task involves preserving formatting while changing content in .docx
---

# python-docx

Programmatic manipulation of .docx Word documents using the `python-docx` library.

## Setup

```bash
# Install (Ubuntu/Debian without venv)
pip install python-docx --break-system-packages

# Or in a venv
pip install python-docx
```

## Core Concepts

### Document Structure
- `Document(path)` — open/create a docx
- `doc.paragraphs` — list of paragraph objects (flattened, NOT hierarchical)
- `doc.tables` — list of table objects
- `doc.sections` — page layout (margins, page size)
- `para.style.name` — the Word style applied (e.g. 'Heading 1', 'List Paragraph')
- `para.runs` — inline text segments with shared formatting
- `para.text` — concatenated text of ALL runs in the paragraph

### Run Formatting
Each `run` carries: `bold`, `italic`, `font.size`, `font.color.rgb`, `font.name`
- Setting `run.text = ""` clears text but preserves the run's formatting
- `run.bold = True/False/None` (None = inherit from style)

## ⚠️ PITFALL: Hyperlinks Are Invisible to .runs

**This is the #1 python-docx trap.** Text inside `<w:hyperlink>` elements is NOT exposed by `para.runs` or `para.text`. A paragraph showing "URL Shortener – description" in Word may appear as only "– description" via python-docx.

The XML structure looks like:
```xml
<w:p>
  <w:r><w:rPr><w:b/></w:rPr></w:r>          <!-- empty bold run -->
  <w:hyperlink r:id="rId15">                  <!-- INVISIBLE to .runs -->
    <w:r><w:rPr><w:b/></w:rPr><w:t>URL Shortener</w:t></w:r>
  </w:hyperlink>
  <w:r><w:t>– description text</w:t></w:r>   <!-- visible in .runs -->
</w:p>
```

### How to Detect Hyperlinks
```python
from docx.oxml.ns import qn

for child in para._element:
    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
    if tag == 'hyperlink':
        for r in child.findall(qn('w:r')):
            for t in r.findall(qn('w:t')):
                print(f"Hidden hyperlink text: {t.text}")
```

### How to Manipulate Hyperlink Text
```python
def set_hyperlink_text(para, new_text):
    for child in para._element:
        if child.tag == qn('w:hyperlink'):
            for r in child.findall(qn('w:r')):
                for t in r.findall(qn('w:t')):
                    t.text = new_text
                # Ensure bold if needed
                rpr = r.find(qn('w:rPr'))
                if rpr is not None and rpr.find(qn('w:b')) is None:
                    from docx.oxml import OxmlElement
                    rpr.append(OxmlElement('w:b'))
            # Remove extra empty runs inside hyperlink
            hr = child.findall(qn('w:r'))
            for r in hr[1:]:
                child.remove(r)
            break
```

## ⚠️ PITFALL: Missing <w:t> Elements After ClearingAfter clearing text, the `<w:t>` child element may be removed entirely. You must ensure it exists before setting text:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def ensure_t_element(run_elem):
    """Ensure a w:r element has a w:t child, return it."""
    t_elems = run_elem.findall(qn('w:t'))
    if t_elems:
        return t_elems[0]
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    run_elem.append(t)
    return t

# Usage after clearing:
for t in run_elem.findall(qn('w:t')):
    t.text = ""   # This preserves the element

# But if you did: run_elem.remove(t_elem), you need ensure_t_element()
```

## ⚠️ PITFALLS: Cloning paragraphs & rebuilding runs (resume template surgery)

Discovered while rewriting a resume template ([Name]'s Calibri template, Aug 2026):

1. **Cloning paragraphs duplicates `w14:paraId`/`w14:textId`.** `copy.deepcopy(para._element)` + `addnext()` copies Word's paragraph IDs, producing duplicate IDs in the file (Word tolerates it, validators may not). Strip them after cloning:
   ```python
   for attr in ('{http://schemas.microsoft.com/office/word/2010/wordml}paraId',
                '{http://schemas.microsoft.com/office/word/2010/wordml}textId'):
       if attr in clone.attrib:
           del clone.attrib[attr]
   ```
2. **Adjacent runs can carry a Hyperlink character style (`w:rStyle`).** When rebuilding a "bold name + description" bullet, if you capture the rPr template from the first *regular* run next to a hyperlink, you may inherit `w:rStyle` pointing at an underline/blue style — the description renders underlined. When building description runs, strip `w:rStyle`, `w:u`, `w:b`, `w:bCs` from the copied rPr. Only the name run inside `<w:hyperlink>` should keep the style.
3. **Trailing space inside a hyperlink run gets underlined.** Put the separator space in its own run OUTSIDE the `<w:hyperlink>`.
4. **Reuse the original run's rPr as the template** (deepcopy before clearing the paragraph), then set text on new runs — preserves Cambria/Calibri, size, color without touching styles.xml.
5. **Fitting to one page: measure, don't eyeball.** Render with metric-compatible fonts (see next section), then measure the last line's yMin with `pdftotext -bbox out.pdf -` (page height 842pt; bottom printable limit ≈ 842 − bottom_margin, e.g. 770). Compare against the ORIGINAL template's fill — a template that already renders at y≈770 is maxed out. Iterate: trim text → re-render → re-measure (`pdfinfo | grep Pages` is coarse; the bbox number tells you how much room remains). Levers in order: paragraph `w:spacing w:after` on bullet paragraphs (200→80→60→40 twips), trimming filler words, then swapping the least-relevant section. When adding content to a full page, budget every line: one 12pt text line ≈ 16-17pt of page height.

## ⚠️ PITFALL: Render-verification needs metric-compatible fonts

LibreOffice without **Caladea/Carlito** (metric-compatible with Cambria/Calibri) substitutes DejaVu, which is wider — a doc that fits one page in Word falsely renders as 2 pages in LO. Install `fonts-crosextra-caladea fonts-crosextra-carlito` (and `libreoffice-writer`; core-only installs fail with "source file could not be loaded"). Verify with `fc-match Cambria` before trusting a page-count check. If Word is installed on Windows, `powershell.exe` COM (Word.Application → SaveAs wdFormatPDF=17) is the most faithful render; fails with 0x80040154 when Word isn't installed/registered.

## ⚠️ PITFALL: The user edited the file — diff first, edit incrementally, NEVER rebuild

The "idempotent rebuild" pattern above is ONLY safe while the user hasn't touched the file. The moment the user says "I made formatting changes, keep them" (or edits the docx in Word between runs), a rebuild-from-template wipes their work. Workflow that preserves it:

1. `cp real.docx /tmp/theirs.docx` BEFORE running anything.
2. **Find what they changed:** regenerate your clean build to a temp path (sed the OUT path), render BOTH to PDF, compare word positions via `pdftotext -bbox` (same y with x-drift that grows with position = font weight/size change; bold vs regular widths diverge linearly). Then tally XML attributes — normalize quote style (`'`→`"`) and empty-element serialization (`<w:x/>` vs `<w:x></w:x>`; Word writes expanded empties, python-docx self-closes) or raw-string diffs are noise. Run-count growth ALONE is Word's run-splitting on save, not a formatting change. `w:p` count, spacing/ind/jc/font/sz tallies, and sectPr are the real signals.
3. Apply new content as INCREMENTAL edits on THEIR file, then save. python-docx preserves untouched paragraphs in the tree.
4. **The Word non-bold trap:** Word writes `<w:b w:val="0"/>` for explicitly non-bold runs — presence checks for `w:b` misreport these as bold. Read the `w:val` attribute. A user's "formatting change" is often exactly this: bold label + regular content per line, which also renders ~5% narrower than all-bold. When replicating the pattern in inserted lines, deepcopy the label run's rPr and the content run's rPr separately.
5. **Clone rPr templates BEFORE rewriting.** Deepcopying a paragraph that has already been rebuilt inherits the NEW content's rPr — e.g. cloning a paragraph whose hyperlink run is now a non-bold URL run makes the clone's name render non-bold. Capture templates from the pristine source, or after a rewrite grab the bold template from the name run (first non-hyperlink run).

### The run-splitting text-vanishing trap (Word-split runs + rPr-only runs)

Word-split runs caused a full description to vanish mid-session. The failure chain: a project paragraph's description was split by Word into [space run, desc run 1, desc run 2, rPr-only run]. An edit loop setting `t.text = new_text if i == last else ""` emptied every run EXCEPT the last — which had NO `<w:t>` child, so `for t in r.findall(qn('w:t'))` matched nothing and wrote nothing. Net result: description gone, silently.

Rules that prevent it:
- **Project/bullet paragraphs: the hyperlink is NOT a direct `w:r` child.** Direct runs are [space run, description run(s)] — "edit run[0]" hits the SPACE run, not the description. Target the last run that actually CONTAINS the text (scan `w:t` contents, don't assume by index), or rebuild the paragraph.
- **Before any multi-run edit loop, verify each run has a `w:t`** (`len(r.findall(qn('w:t')))`). rPr-only runs are common after Word saves — they must be skipped, never treated as text targets.
- **If content is already clobbered, rebuild the paragraph deterministically:** capture the hyperlink run's rPr (bold name template) and the first direct run's rPr (description template) BEFORE clearing; clear all runs + hyperlinks; re-add hyperlink(name) + space run + description run. Don't try to patch fragments back together.
- Cross-check every edit with a render: `pdftotext -layout` of the paragraph in question — the vision model and PDF text agree on what's actually on the page; the XML alone misleads when runs are empty-but-present.


## One-page layout surgery (fitting & restructuring)

Learned iterating on a one-page resume (Aug 2026). Complements the cloning pitfalls above:

- **Line budget:** 12pt Cambria/Caladea on A4 ≈ 95-100 chars/line. To keep an entry at N lines, total chars ≤ N×95. Trim description text first — it's the cheaper lever than spacing (text trims are predictable; spacing tweaks across 12 bullets ≈ 1 line per 6pt).
- **Widow check:** a single word wrapping onto its own line (e.g. "CI." dangling) reads as a glitch. Trim ~10-15 chars from that paragraph until it fits; don't re-tune spacing for one paragraph.
- **Right-aligned date lines are full-width:** dates pushed right by trailing spaces/tabs cannot absorb extra text on the same line — appending a role descriptor makes the date wrap to line 2. Put positioning text in a separate summary paragraph instead of the title line.
- **Section reorder:** move a whole section by walking body children from its header element with `getnext()`, stopping at non-`w:p` tags (keeps `w:sectPr` last), then `body.remove(el)` + `target_header.addprevious(el)` per element — order is preserved, no index bookkeeping.
- **One link affordance per line (user preference):** the two-run mixed hyperlink below works technically, but this user rejected visible URLs outright ("why waste extra space, why not just make the name clickable like before"). Visible URLs cost ~40 chars per entry, force description trims, and duplicate the affordance — the GitHub link already lives in the header. Default for project lines: name-only clickable hyperlink, no visible URL text.
- **Mixed-format hyperlink:** one `<w:hyperlink>` can hold two runs with different rPr (bold name + non-bold underlined URL) sharing a single `relate_to` rId — both clickable, visual hierarchy intact. (Use only if the user explicitly asks for visible URLs.)
- **Idempotent rebuild:** when iterating on a document many times, write a script that re-opens the ORIGINAL template each run and applies every edit from scratch. Iterations never compound artifacts and the original stays untouched.
- **Date-typo fixes are run-text surgery:** `"–Present"` → `"– Present"` via `t.text.replace('\u2013Present', '\u2013 Present')` on the containing run — safe because it doesn't touch alignment spacing.

## Common Patterns

### Read All Text (Including Hyperlinks)
```python
from docx import Document
from docx.oxml.ns import qn

doc = Document("file.docx")
for i, para in enumerate(doc.paragraphs):
    texts = []
    for child in para._element:
        tag = child.tag.split('}')[-1]
        if tag == 'r':
            for t in child.findall(qn('w:t')):
                if t.text: texts.append(t.text)
        elif tag == 'hyperlink':
            for r in child.findall(qn('w:r')):
                for t in r.findall(qn('w:t')):
                    if t.text: texts.append(t.text)
    if texts:
        print(f"[{i}] {' '.join(texts)}")
```

### Replace Paragraph Text Preserving Format
```python
def clear_paragraph_text(para):
    """Remove all text including inside hyperlinks."""
    for child in para._element:
        if child.tag == qn('w:r'):
            for t in child.findall(qn('w:t')):
                t.text = ""
        elif child.tag == qn('w:hyperlink'):
            for r in child.findall(qn('w:r')):
                for t in r.findall(qn('w:t')):
                    t.text = ""

# Then set text on specific runs:
clear_paragraph_text(para)
para.runs[0].text = "new text"
para.runs[0].bold = True
```

### Restructure Document Content (Template Pattern)
When transforming a template docx for different content:
1. Open the template
2. Map paragraph indices to content sections
3. For each paragraph to modify:
   - If it has hyperlinks: manipulate at XML level (see above)
   - If plain runs: clear + set on runs[0] / runs[1] for bold+normal
4. Save to new file (preserves all styles, fonts, margins, page layout)

### Bold Label + Normal Description Pattern
```python
# Common in resumes: "Label: " (bold) + "content" (normal)
para.runs[0].text = "Label: "
para.runs[0].bold = True
para.runs[1].text = "the actual content"
para.runs[1].bold = False
```

### Tables
```python
for table in doc.tables:
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        print(cells)
```

### Sections & Margins
```python
section = doc.sections[0]
# Measurements in EMU (English Metric Units): 1 inch = 914400 EMU
section.top_margin    # e.g. 457200 = 0.5 inch
section.page_width    # e.g. 7560310 ≈ A4 width
section.page_height   # e.g. 10692130 ≈ A4 height
```

## What python-docx Can NOT Do

- Pixel-perfect layout matching (margins, exact page breaks)
- Complex nested formatting that depends on Word's rendering engine
- Macros/VBA
- .doc (old binary format) — use libreoffice to convert first
- Track changes, comments (limited support)
- Headers/footers per-section content (basic only)

## Full Working Example


## Debugging Tips

- Always dump the XML of problematic paragraphs: `etree.tostring(para._element, pretty_print=True).decode()`
- Check `len(para.runs)` vs actual visible text — mismatch usually means hidden elements (hyperlinks, bookmarks)
- Run indexing is 0-based and matches the order paragraphs appear in the XML
- Styles reference internal IDs (e.g. '978') not human-readable names — use `para.style.name` for the readable name
