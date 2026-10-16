"""[designed: T69] Optional desktop entry; game imports remain Qt-free."""
import argparse
import sys
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description='goal2 desktop country management')
    parser.add_argument('--template',type=Path);parser.add_argument('--data',required=True,type=Path)
    parser.add_argument('--save',type=Path,default=Path('.cache/desktop.g2save'))
    parser.add_argument('--resume',type=Path);parser.add_argument('--country',type=int,default=1)
    args=parser.parse_args(argv)
    if bool(args.template)==bool(args.resume):parser.error('choose exactly one of --template or --resume')
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Desktop needs PySide6. Install the desktop extra: python3 -m pip install ".[desktop]"',file=sys.stderr)
        return 2
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    try:
        model=(DesktopModel.from_save(args.resume,args.data) if args.resume
               else DesktopModel.open(args.template,args.data,args.save,country=args.country))
    except (OSError,ValueError) as exc:
        print(str(exc),file=sys.stderr);return 2
    app=QApplication.instance() or QApplication(sys.argv[:1])
    window=ManagementWindow(model);window.show()
    try:
        return app.exec()
    finally:
        # [designed: T69] Destroy widgets before QApplication/X11 plugin teardown.
        from PySide6.QtCore import QCoreApplication,QEvent
        window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.shutdown()

if __name__=='__main__':raise SystemExit(main())
