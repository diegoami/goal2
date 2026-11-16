"""[designed: T69] Optional desktop entry; game imports remain Qt-free."""
import argparse
import sys
from pathlib import Path


def main(argv=None):
    parser=argparse.ArgumentParser(description='goal2 desktop country management')
    # [designed: owner, 2026-11-02, T153] Without --data (and --core-boot) the defaults are the player's per-user data
    # folder, filled on first start by the import dialog (goal2/desktop/data_setup.py), and the saves folder beside it.
    parser.add_argument('--template',type=Path);parser.add_argument('--data',type=Path)
    parser.add_argument('--save',type=Path)
    parser.add_argument('--resume',type=Path);parser.add_argument('--country',type=int)
    # [designed: owner, 2026-10-22, #321; T105] --core opens the original's own game (goal2/core) from a savestate
    # in its key read; --resume with a core save (G2C1, docs/core.md) resumes it. The --template route is unchanged.
    parser.add_argument('--core',type=Path)
    # [designed: owner, 2026-10-22; T106] --core-boot opens Launch over the original's own new game, booted to its DOS
    # date call (docs/core.md): [designed: owner, 2026-11-13, #705; T222] from the player's GOAL.EXE, or from the
    # recorded state there (e039-r0005-date-call.sav), which developers and the tests keep using; GOAL.DAT is read
    # from --data.
    parser.add_argument('--core-boot',type=Path)
    args=parser.parse_args(argv)
    if args.data is None:
        if args.core_boot is not None:parser.error('--core-boot needs --data')
        status=_player_defaults(args)
        if status is not None:return status
    if args.save is None:args.save=DEVELOPER_SAVE
    if args.core_boot is not None and (args.core or args.template or args.country is not None or args.resume):
        parser.error('--core-boot excludes --core, --template, --country and --resume')
    if args.core_boot is not None:
        return _core(args)
    if args.core is not None and (args.template or args.country is not None):parser.error('--core excludes --template and --country')
    if args.core is not None and args.resume is not None:parser.error('--core excludes --resume')
    if args.core is not None or (args.resume is not None and _core_save(args.resume)):
        return _core(args)
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

DEVELOPER_SAVE=Path('.cache/desktop.g2save')   # [designed: T69] the default save of a run given --data


def _player_defaults(args):
    """[designed: owner, 2026-11-02, T153] Fill the defaults from the player's data folder, importing it first if
    it is incomplete: --data its GOAL.DAT; with no other route flag, --core-boot its GOAL.EXE (the core route's new
    career, T222); --save the saves folder's
    desktop.g2core (desktop.g2save on the --template route). Returns an exit status if the desktop cannot start."""
    from goal2.desktop import data_setup
    try:
        target=data_setup.ensure()
    except ImportError:
        print('Desktop needs PySide6. Install the desktop extra: python3 -m pip install ".[desktop]"',file=sys.stderr)
        return 2
    except data_setup.SetupError as exc:
        print(str(exc),file=sys.stderr);return 2
    if target is None:
        print('goal2 needs its data folder: '+data_setup.intro(data_setup.paths()),file=sys.stderr);return 2
    args.data=target.goal_dat
    if not (args.core or args.template or args.country is not None or args.resume):args.core_boot=target.boot
    if args.save is None:
        args.save=target.save if args.core_boot is not None or args.core is not None else target.saves/'desktop.g2save'
    return None


def _core_save(path):
    """[designed: T105] A core save starts with G2C1 (goal2/core/runner.py MAGIC)."""
    try:
        with open(path,'rb') as f:return f.read(4)==b'G2C1'
    except OSError:
        return False


def _core(args):
    """[designed: T105] The core route: the main window over a CoreModel (goal2/desktop/core_model.py)."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Desktop needs PySide6. Install the desktop extra: python3 -m pip install ".[desktop]"',file=sys.stderr)
        return 2
    from goal2.desktop.core_model import CoreModel
    from goal2.desktop.window import window_for
    save=args.save if args.save!=DEVELOPER_SAVE else Path('.cache/desktop.g2core')
    if args.core_boot is not None:
        return _core_launch(args,save)
    try:
        model=CoreModel.from_save(args.resume,args.data) if args.resume else CoreModel.open(args.core,args.data,save)
    except ValueError as exc:
        print(str(exc),file=sys.stderr);return 2
    app=QApplication.instance() or QApplication(sys.argv[:1])
    window=window_for(model);window.show()
    try:
        return app.exec()
    finally:
        from PySide6.QtCore import QCoreApplication,QEvent
        window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.shutdown()

def _core_launch(args,save):
    """[designed: T106] Launch on the core route: New career runs the original's new game, then the main window."""
    from PySide6.QtWidgets import QApplication
    from goal2.desktop.launch import LaunchWindow
    from goal2.desktop.window import window_for
    app=QApplication.instance() or QApplication(sys.argv[:1])
    windows=[]
    def opened(model):
        window=window_for(model);window.show();windows.append(window)
    windows.append(LaunchWindow(args.data,None,save,opened,core_boot=args.core_boot));windows[-1].show()
    try:
        return app.exec()
    finally:
        from PySide6.QtCore import QCoreApplication,QEvent
        for window in windows:window.close();window.deleteLater()
        QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
        app.shutdown()

if __name__=='__main__':raise SystemExit(main())
