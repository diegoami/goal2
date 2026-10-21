"""[designed: T69] Optional desktop entry; game imports remain Qt-free."""
import argparse
import sys
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description='goal2 desktop country management')
    parser.add_argument('--template',type=Path);parser.add_argument('--data',required=True,type=Path)
    parser.add_argument('--save',type=Path,default=Path('.cache/desktop.g2save'))
    parser.add_argument('--resume',type=Path);parser.add_argument('--country',type=int)
    args=parser.parse_args(argv)
    # [designed: T86] Without --resume or --country the Launch window chooses; those two
    # flags keep opening management directly for scripts.
    direct=args.resume is not None or args.country is not None
    if args.resume is not None and (args.template or args.country is not None):parser.error('--resume excludes --template and --country')
    if args.country is not None and not args.template:parser.error('--country needs --template')
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Desktop needs PySide6. Install the desktop extra: python3 -m pip install ".[desktop]"',file=sys.stderr)
        return 2
    from goal2.desktop.model import DesktopModel
    from goal2.desktop.window import ManagementWindow
    windows=[]
    def opened(model):
        window=ManagementWindow(model);window.show();windows.append(window)
    if direct:
        try:
            model=(DesktopModel.from_save(args.resume,args.data) if args.resume
                   else DesktopModel.open(args.template,args.data,args.save,country=args.country))
        except (OSError,ValueError) as exc:
            print(str(exc),file=sys.stderr);return 2
    app=QApplication.instance() or QApplication(sys.argv[:1])
    if direct:opened(model)
    else:
        from goal2.desktop.launch import LaunchWindow
        windows.append(LaunchWindow(args.data,args.template,args.save,opened));windows[-1].show()
    try:
        return app.exec()
    finally:
        # [designed: T69] Destroy widgets before QApplication/X11 plugin teardown.
        from PySide6.QtCore import QCoreApplication,QEvent
        for window in windows:window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.shutdown()

if __name__=='__main__':raise SystemExit(main())
