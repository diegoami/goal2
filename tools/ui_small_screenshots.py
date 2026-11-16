"""[designed: T216, #667] Capture small-screen states at task sizes using private inputs and explicitly owned help/record fixtures."""
import argparse,json,sys,tempfile,os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    p=argparse.ArgumentParser(description=__doc__.splitlines()[0]);p.add_argument('output',type=Path);args=p.parse_args()
    from PySide6.QtWidgets import QApplication
    from goal2.desktop import data_setup,fixed_page
    from goal2.desktop.model import DesktopModel
    from goal2.ui import theme,replays,saves
    from goal2.ui.window import Window
    from goal2.ui.home import HomeScreen
    from goal2.ui.s05_bulletin import BulletinScreen
    from goal2.ui.s21_save import SaveScreen,QuestionScreen,QUIT_TEXT,SAVE_QUESTION
    from goal2.ui.s22_help import HelpScreen
    from goal2.tests.test_ui_replay_t181 import frames
    app=QApplication.instance() or QApplication([]);theme.install(app);args.output.mkdir(parents=True,exist_ok=True);records=[]
    with tempfile.TemporaryDirectory(prefix='goal2-small-shots-') as tmp:
        target=data_setup.paths(Path(tmp)/'goal2');data_setup.import_folder(ROOT/'.cache',target,data_setup.WINDOW_MANIFEST)
        target.help.unlink(missing_ok=True)
        w=Window(target)
        def shot(name,context):
            sizes=((1440,1080),(1440,900),(2110,1213),(1440,1061)) + (((720,450),) if isinstance(w.current(),HelpScreen) else ())
            for width,height in sizes:
                w.resize(width,height);w.show()
                for _ in range(4):app.processEvents()
                folder=args.output/f'{width}x{height}';folder.mkdir(exist_ok=True);w.grab().save(str(folder/name))
                records.append(dict(screen=type(w.current()).__name__,picture=name,context=context,requested=[width,height],actual=[w.width(),w.height()],problems=fixed_page.problems(w)))
        try:
            w.push(HomeScreen(w));shot('home.png','placeholder without an open career')
            model=DesktopModel.open(target.data/data_setup.TEMPLATE_NAME,target.goal_dat,Path(tmp)/'career',country=20)
            model.new_campaign(20,2028);model.rename_manager('K Ees');model.mark_saved();w.open_career(model)
            w.push(HelpScreen(w,w.current(),target));shot('s22-help-missing.png','missing optional help');w.pop()
            target.help.write_bytes(b'OWNED STAND-IN HELP\r\n'+b'A complete line of help text.\r\n'*100+b'\x1a')
            w.push(HelpScreen(w,w.current(),target));shot('s22-help.png','owned stand-in help, not original help bytes');w.pop()
            from goal2.core import Core,views
            wait=Core.start((ROOT/'.cache/e038-r0001-after-name-1.sav').read_bytes())
            assert wait.kind=='bulletin'
            page=views.bulletin(wait.state)
            w.push(BulletinScreen(w,[page],lambda:None));shot('s05-bulletin.png','real original bulletin projection from kept E038 input');w.pop()
            screen=w.push(SaveScreen(w,w.current(),model));screen.field.set_text('Road to the championship');shot('s21-save.png','name entry over the desk')
            screen.say('The game was not saved: '+r'C:\Users\runneradmin\AppData\Local\Temp'+(r'\subfolder'*25)+r'\a-name.g2game: Access denied. Nothing was replaced.');shot('s21-save-failed.png','authored Windows-style failure message, all text retained')
            screen.say('');screen.save();screen=w.push(SaveScreen(w,w.current(),model));screen.save();shot('s21-replace.png','actual named-save replacement question');w.pop()
            for name,head,question in (('s21-quit.png','Quit',QUIT_TEXT),('s21-save-question.png','Save',SAVE_QUESTION)):
                w.push(QuestionScreen(w,w.current(),'quit',head,question,lambda:None,lambda:None,cancel=lambda:None));shot(name,'question over the desk');w.pop()
            goal=dict(frames=frames(),countries=['Holland','Romania'],score=[0,1],minute=3,scorer='A Player',kits=dict(shirt=[1,2],keeper=[3,4]),kind='FRIENDLY')
            screen=replays.name_recording(w,w.current(),'goal',goal,lambda:None);screen.field.set_text('A goal to remember');shot('s21-save-goal.png','owned recording fixture, name-entry UI');screen.save()
            for i in range(10):replays.write(target.root/'recordings','goal',str(i)+' recorded goal',goal)
            replays.open_list(w,model,'goal');shot('s21-saved-goals.png','bounded list of owned recording fixtures');w.pop()
            replays.open_list(w,model,'summary');shot('s21-saved-summaries.png','empty summary list');w.pop()
        finally:w.leaving=True;w.close();app.processEvents()
    (args.output/'layout-report.json').write_text(json.dumps(records,indent=2)+'\n');bad=[r for r in records if r['problems']]
    print(json.dumps(dict(captures=len(records),problems=bad),indent=2));return bool(bad)
if __name__=='__main__':raise SystemExit(main())
