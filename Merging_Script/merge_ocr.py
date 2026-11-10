#!/usr/bin/env python3
"""Merge a Mistral OCR playground export (pages/page-N/markdown.md + tbl-*.html)
into ONE markdown file, converting HTML tables to pipe tables.

usage: merge_ocr.py <export_dir> <out.md>
"""
import re, sys, pathlib
from bs4 import BeautifulSoup

LINK = re.compile(r'\[(tbl-\d+)\.html\]\(\1\.html\)')

def cell_text(td):
    for br in td.find_all('br'):
        br.replace_with(' / ')
    t = re.sub(r'\s+', ' ', td.get_text()).strip()
    return t.replace('|', '\\|')

def grid(rows):
    """Expand colspan/rowspan into a rectangular grid of strings."""
    g, pending = [], {}
    for r, tr in enumerate(rows):
        row, c = [], 0
        cells = tr.find_all(['td', 'th'])
        it = iter(cells)
        while True:
            if (r, c) in pending:
                row.append(pending.pop((r, c))); c += 1; continue
            cell = next(it, None)
            if cell is None:
                break
            cs, rs = int(cell.get('colspan', 1)), int(cell.get('rowspan', 1))
            txt = cell_text(cell)
            for k in range(cs):
                row.append(txt)
                for rr in range(1, rs):
                    pending[(r + rr, c + k)] = txt
            c += cs
        while (r, c) in pending:
            row.append(pending.pop((r, c))); c += 1
        g.append(row)
    w = max(map(len, g)) if g else 0
    return [r + [''] * (w - len(r)) for r in g]

def flat_header(hrows):
    cols = []
    for j in range(len(hrows[0])):
        parts = []
        for r in hrows:
            p = r[j]
            if p and (not parts or parts[-1] != p):
                parts.append(p)
        cols.append(' – '.join(parts))
    return cols

def md_table(header, body):
    out = ['| ' + ' | '.join(header) + ' |',
           '|' + '|'.join(['---'] * len(header)) + '|']
    out += ['| ' + ' | '.join(r) + ' |' for r in body]
    return '\n'.join(out)

def convert(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    thead = table.find('thead')
    all_rows = table.find_all('tr')
    if thead:
        hcount = len(thead.find_all('tr'))
    else:
        hcount = 0
    g = grid(all_rows)
    if hcount == 0 and len(g[0]) % 2 == 0 and len(g[0]) <= 6:
        # label/value grid (spec boxes): render as list
        lines = []
        for r in g:
            for k in range(0, len(r), 2):
                if r[k] or r[k + 1]:
                    lines.append(f'- **{r[k]}**: {r[k+1]}')
        return '\n'.join(lines)
    if hcount == 0:
        return md_table([f'col{i+1}' for i in range(len(g[0]))], g)
    return md_table(flat_header(g[:hcount]), g[hcount:])

def main(src, out):
    src = pathlib.Path(src)
    pages = sorted((src / 'pages').glob('page-*'),
                   key=lambda p: int(p.name.split('-')[1]))
    chunks = []
    for p in pages:
        md = (p / 'markdown.md').read_text(encoding='utf-8')
        md = LINK.sub(lambda m: convert((p / f'{m.group(1)}.html').read_text(encoding='utf-8')), md)
        n = p.name.split('-')[1]
        chunks.append(f'<!-- page {n} -->\n\n{md.strip()}\n')
    pathlib.Path(out).write_text('\n'.join(chunks), encoding='utf-8')

if __name__ == '__main__':
    main(*sys.argv[1:3])
