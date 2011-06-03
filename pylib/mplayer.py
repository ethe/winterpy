#!/usr/bin/env python3
# vim:fileencoding=utf-8

import os
import stat

from subprocessio import Subprocess, PIPE

class MPlayer:
  def __init__(self, fifo=os.path.expanduser('~/.mplayer/fifo')):
    self.fifo = fifo
    if not os.path.exists(self.fifo):
      os.mkfifo(fifo, 0o600)
    if not stat.S_ISFIFO(os.stat(fifo).st_mode):
      raise MplayerError('文件存在但是不是 FIFO：%s' % fifo)
    cmd = ['mplayer', '-nolirc', '-idle', '-really-quiet',
           '-input', fifo,
          '-input', 'default-bindings']
    self.sub = Subprocess(cmd, stdin=PIPE, stdout=PIPE)

  def docmd(self, cmd):
    if not os.path.exists(self.fifo):
      raise MplayerError('FIFO 文件丢失')

    # 任何命令都会导致已暂停者继续播放
    self.playing = True
    if not cmd.endswith('\n'):
      cmd += '\n'
    with open(self.fifo, 'w') as f:
      f.write(cmd)
    time.sleep(0.2)
    return self.sub.output()

class MplayerError(Exception): pass
