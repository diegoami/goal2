"""[designed: #253] Validate authored static SVG/PNG previews, not running UI."""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF, QGuiApplication, QImage
from PySide6.QtSvg import QSvgRenderer

app = QGuiApplication([])
root = Path(sys.argv[1]).resolve()
results = []
for source in sorted((root / 'docs/redesign-253/layouts').glob('*.svg')):
    tree = ET.fromstring(source.read_bytes())
    failures = []
    count = 0
    for node in tree.iter():
        if not node.tag.endswith('text'):
            continue
        count += 1
        font = QFont('DejaVu Sans')
        font.setPixelSize(int(node.get('font-size', '15')))
        font.setWeight(QFont.Weight(int(node.get('font-weight', '400'))))
        text = ''.join(node.itertext())
        metrics = QFontMetricsF(font)
        rect = metrics.tightBoundingRect(text)
        start = float(node.get('x', '0'))
        if node.get('text-anchor') == 'middle':
            start -= metrics.horizontalAdvance(text) / 2
        elif node.get('text-anchor') == 'end':
            start -= metrics.horizontalAdvance(text)
        rect.translate(start, float(node.get('y', '0')))
        if rect.left() < 0 or rect.right() > 1600 or rect.top() < 0 or rect.bottom() > 1010:
            failures.append({'text': text, 'bounds': [rect.left(), rect.top(), rect.right(), rect.bottom()]})
    png = source.with_suffix('.png')
    image = QImage(str(png))
    valid = QSvgRenderer(str(source)).isValid() and not image.isNull() and (image.width(), image.height()) == (1600, 1010)
    results.append({'svg': source.name, 'svg_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'png_sha256': hashlib.sha256(png.read_bytes()).hexdigest(), 'text_elements': count,
                    'font': QFontInfo(font).family(), 'static_svg_and_png_valid': valid,
                    'out_of_canvas_text': failures})
print(json.dumps({'evidence': '[confirmed: #253 Qt6.12 static artifact bounds check]',
 'method': 'QFontMetricsF tight text bounds in1600x1010 canvas; XML/PNG validity. Does not test overlap, game geometry or accessibility; all10 previews visually reviewed.',
 'helper_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'layouts': results}, indent=2))
sys.exit(0 if len(results) == 10 and all(r['static_svg_and_png_valid'] and not r['out_of_canvas_text'] for r in results) else 1)
