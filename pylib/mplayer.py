#!/usr/bin/env python3
# vim:fileencoding=utf-8

import os
import re

from subprocessio import Subprocess, PIPE

re_ans = re.compile(r'^ANS_(?P<name>[^=]+)=(?P<value>.+)$', re.MULTILINE)

class MPlayer:
  def __init__(self):
    cmd = ['mplayer', '-nolirc', '-idle', '-quiet', '-slave']
    self.sub = Subprocess(cmd, stdin=PIPE, stdout=PIPE)
    self.currentfile = None

  @property
  def length(self):
    return self.getans('get_time_length')
  @property
  def pos(self):
    return self.getans('get_time_pos')
  @property
  def filename(self):
    '''注意：只有文件名，没有路径'''
    return self.getans('get_file_name')
  @property
  def paused(self):
    return self.getproperty('pause')
  @property
  def looping(self):
    return self.getproperty('loop') != -1

  def playfile(self, file):
    self.docmd('loadfile %s' % file, False)
    self.currentfile = file

  def loop(self, state=True):
    # loop 命令的第二个参数表示是否为绝对值。默认是相对值
    if state:
      self.docmd('loop 0 1')
    else:
      self.docmd('loop -1 1')

  def mute(self, state=True):
    if state:
      self.docmd('mute 1')
    else:
      self.docmd('mute 0')

  def seek(self, pos, absolute=False):
    cmd = 'seek %d' % pos
    if absolute:
      cmd += ' 2'
    self.docmd(cmd)

  def quit(self):
    self.docmd('quit')
    self.sub = None

  def __del__(self):
    if self.sub:
      self.docmd('quit')

  def getproperty(self, prop):
    return self.getans('get_property %s' % cmd)

  def getans(self, cmd):
    output = self.docmd(cmd)
    m = re_ans.search(output)
    v = m.group('value')
    if v.startswith("'"):
      return v[1:-1]
    elif v == 'yes':
      return True
    elif v == 'no':
      return False
    else:
      try:
        return float(v)
      except ValueError:
        return v

  def docmd(self, cmd, pausing_keep=True):
    if not cmd.endswith('\n'):
      cmd += '\n'
    if pausing_keep:
      cmd = 'pausing_keep ' + cmd
    self.sub.input(cmd)
    time.sleep(0.2)
    return self.sub.output()

class MplayerError(Exception): pass
