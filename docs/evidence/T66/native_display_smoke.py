"""[designed: T66] Reproducible bounded validation command; no original bytes."""
import os,subprocess,sys
code="""import pygame
pygame.init()
s=pygame.display.set_mode((640,360))
s.fill((17,33,49));pygame.display.flip()
pygame.event.post(pygame.event.Event(pygame.QUIT))
assert any(e.type==pygame.QUIT for e in pygame.event.get())
print('PASS native SDL window',pygame.display.get_driver(),pygame.version.ver,pygame.get_sdl_version())
pygame.quit()
"""
env=dict(os.environ,SDL_AUDIODRIVER='dummy')
env.pop('SDL_VIDEODRIVER',None)
try:
 result=subprocess.run([sys.executable,'-c',code],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8)
 print(result.stdout.decode(errors='replace'));print('native_returncode',result.returncode)
except subprocess.TimeoutExpired as exc:print('Native window smoke exceeded8s; owned child reaped by subprocess.run; no service changes')
