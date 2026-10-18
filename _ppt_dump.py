import sys, zipfile
import xml.etree.ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

path = sys.argv[1]
start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
end = int(sys.argv[3]) if len(sys.argv) > 3 else 10 ** 6
out = open(sys.argv[4], 'w', encoding='utf-8') if len(sys.argv) > 4 else None

def emit(*parts):
    s = ' '.join(str(p) for p in parts).replace('\xa0', ' ').replace('\u000b', ' ')
    print(s, file=out if out else sys.stdout)

z = zipfile.ZipFile(path)
pres = ET.fromstring(z.read('ppt/presentation.xml'))
rels = ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
relmap = {r.get('Id'): r.get('Target') for r in rels}

order = []
for sldId in pres.find(P + 'sldIdLst'):
    order.append(relmap[sldId.get(R + 'id')])

emit('TOTAL_SLIDES', len(order))

def shape_text(sp):
    lines = []
    for p in sp.iter(A + 'p'):
        txt = ''.join(t.text or '' for t in p.iter(A + 't')).strip()
        if txt:
            lines.append(txt)
    return lines

for idx, target in enumerate(order, 1):
    if idx < start or idx > end:
        continue
    name = 'ppt/' + target.lstrip('/').replace('ppt/', '')
    root = ET.fromstring(z.read(name))
    emit(f'===== SLIDE {idx} =====')
    tree = root.find(P + 'cSld').find(P + 'spTree')
    for node in list(tree):
        tag = node.tag
        if tag == P + 'sp':
            ph = None
            nv = node.find(P + 'nvSpPr')
            if nv is not None:
                nvPr = nv.find(P + 'nvPr')
                if nvPr is not None:
                    phEl = nvPr.find(P + 'ph')
                    if phEl is not None:
                        ph = phEl.get('type')
            lines = []
            for sp in node.findall(P + 'txBody'):
                lines.extend(shape_text(sp))
            if lines:
                prefix = f'[{ph}] ' if ph else ''
                for ln in lines:
                    emit(prefix + ln)
        elif tag == P + 'graphicFrame':
            for tbl in node.iter(A + 'tbl'):
                for tr in tbl.iter(A + 'tr'):
                    cells = []
                    for tc in tr.iter(A + 'tc'):
                        cells.append(' '.join(''.join(t.text or '' for t in p.iter(A + 't')).strip() for p in tc.iter(A + 'p')).strip())
                    emit(' | '.join(cells))
        elif tag == P + 'grpSp':
            for sp in node.iter(P + 'sp'):
                for sp2 in sp.findall(P + 'txBody'):
                    for ln in shape_text(sp2):
                        emit(ln)
    notesname = name.replace('slides/slide', 'notesSlides/notesSlide')
    try:
        nroot = ET.fromstring(z.read(notesname))
        ntexts = [''.join(t.text or '' for t in p.iter(A + 't')).strip() for p in nroot.iter(A + 'p')]
        ntexts = [t for t in ntexts if t]
        if ntexts:
            emit('--- NOTES ---')
            for t in ntexts:
                emit('NOTE: ' + t)
    except KeyError:
        pass
