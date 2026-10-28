"""T144 actual native-window evidence; original fixtures/captures stay private."""
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QPoint,QRect,Qt,Qt
from PySide6.QtWidgets import QApplication,QMainWindow,QSizePolicy,QSizePolicy
from PySide6.QtTest import QTest
from goal2.desktop.country_card import CountryCardView
from goal2.desktop.core_model import CoreModel
from goal2.desktop.core_window import CoreWindow
from goal2.desktop.style import load_fonts
from goal2.tests.test_core_team_panels_t144 import image,FIXTURES
from goal2.tests import requires
from goal2.core import views

p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
files=['goal2/core/views.py','goal2/desktop/country_card.py','goal2/desktop/core_model.py',
       'goal2/desktop/launch.py','goal2/desktop/squad_page.py','goal2/tests/test_core_team_panels_t144.py',
       'measurements/T144/native_probe.py']
files += [str(f.relative_to(ROOT)) for f in sorted((ROOT/'goal2/engine/team_card').glob('*.py'))]
def hashes():return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
source=hashes();head=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
app=QApplication([]);load_fonts();backend=app.platformName();assert backend in ('xcb','windows'),backend
area=app.primaryScreen().availableGeometry();cases=[]
def expose(window,width,height):
    scale=min(1.0,area.width()*0.88/width,area.height()*0.84/height)
    window.resize(round(width*scale),round(height*scale));window.move(area.x()+20,area.y()+20)
    window.show();window.raise_();window.activateWindow()
    assert QTest.qWaitForWindowActive(window,5000),'no actual active native window'
    app.processEvents();QTest.qWait(120);return scale

def capture(window,widget,name,expected):
    app.processEvents();QTest.qWait(80);shot=widget.grab()
    assert widget.bottom <= widget.height()/widget.scale(),(name,'vertical clipping',widget.bottom)
    assert widget.right <= widget.width()/widget.scale(),(name,'horizontal clipping',widget.right)
    assert [b[-1] for b in widget.painted_bars]==expected,(name,'bar counts')
    raster=shot.toImage();scale=widget.scale()*shot.devicePixelRatio()
    for x,y,width,count,filled in widget.painted_bars:
        for i in range(count):
            at=(round((x+(i+0.5)*width/count)*scale),round((y-15)*scale))
            want='#aaaaaa' if filled is not None and i<filled else '#000000'
            assert raster.pixelColor(*at).name()==want,(name,i,at,'actual bar pixel')
    path=out/(name+'.png');assert window.grab().save(str(path))
    assert area.contains(window.frameGeometry()),(name,'off-screen native window',window.frameGeometry(),area)
    cases.append(dict(case=name,native_active=window.isActiveWindow(),device_pixel_ratio=window.devicePixelRatioF(),
                      page_scale=widget.scale(),window=[window.width(),window.height()],
                      bar_cells=expected,bottom=widget.bottom,right=widget.right,
                      screenshot=path.name,screenshot_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

try:
    model=CoreModel.open(requires.CACHE/'e006-r0001-main.sav',requires.CACHE/'GOAL.DAT',requires.CACHE/'T144-never-native-save.g2core')
    before=model.core.save();w=CoreWindow(model);expose(w,1440,900)
    w.core_routes['team info'].click();app.processEvents();QTest.qWait(120)
    data=model.country_card();expected=[b['cells'] for b in data['team_skills']['bars']]+([None]*4 if data['performance'] is None else [b['cells'] for b in data['performance']['bars']])
    for child in [w.core_team_panels,w.core_team_info_back,*[r for _,r in w.tactics]]:
        rect=QRect(child.mapTo(w,QPoint(0,0)),child.size());assert child.isVisible() and w.rect().contains(rect),child.objectName()
    for _,row in w.tactics:assert row.width()>=row.sizeHint().width(),row.objectName()
    capture(w,w.core_team_panels,'team-info',expected)
    w.core_team_info_back.click();app.processEvents();assert w.page_stack.currentIndex()==0
    w.navigate(1);w.team_views.show_view(1);app.processEvents();w.tactics[0][1].setFocus()
    QTest.keyClick(w.tactics[0][1],Qt.Key.Key_Escape);app.processEvents()  # Qt.Key_Escape, original contextual route.
    assert w.team_views.currentIndex()==0
    assert model.core.save()==before,'Core changed before any game action';w.close();app.processEvents()
    for fixture,country,expected in [('selection',7,[21,25,25,9]+[None]*4),('friendly',16,[22,19,20,7,9,12,14,4])]:
        state=image(fixture);original=state.memory_component();host=QMainWindow();card=CountryCardView();host.setCentralWidget(card)
        card.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored)
        expose(host,740,640);host.setProperty('pageScale',card.width()/740)
        card.set_card(views.country_card(state,country),reader=lambda s=state,c=country:views.country_card(s,c))
        capture(host,card,fixture,expected);assert state.memory_component()==original
        host.close();app.processEvents()
    assert hashes()==source,'source changed during native evidence'
    report=dict(head=head,source_sha256=source,source_unchanged=True,platform=platform.platform(),qt_backend=backend,
                available_geometry=[area.x(),area.y(),area.width(),area.height()],cases=cases,core_save_unchanged=True,
                fixture_sha256={k:v[1] for k,v in FIXTURES.items()},passed=True)
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,head=head,backend=backend,cases=len(cases),dpr=[c['device_pixel_ratio'] for c in cases])),flush=True)
except BaseException as error:
    (out/'failed.json').write_text(json.dumps(dict(head=head,source_sha256=source,platform=platform.platform(),qt_backend=backend,
                                                cases=cases,passed=False,error=type(error).__name__+': '+str(error)),indent=2)+'\n')
    raise
