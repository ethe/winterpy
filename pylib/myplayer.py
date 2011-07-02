#!/usr/bin/env python3
# fileencoding=utf-8

'''按喜好随机播放歌曲'''

import os
import sys
import socket
import random
from datetime import datetime
from notify import notify
from path import path

config = {
  'mocpPlaylistFile': os.path.expanduser('~/.moc/playlist.m3u'),
  'mocpConfig'      : os.path.expanduser('~/.moc/config'),
  'playlist'        : os.path.expanduser('~/.moc/playlist.xmocp'),
  'socket'          : os.path.expanduser('~/.moc/xmocp'),
  'useNotify'       : True,
  'notifyOnStartup' : True,
}

class song:
  def __init__(self, file, rank=1000, playedTimes=0):
    self.file = file
    self.rank = rank
    self.playedTimes = playedTimes

  def up(self):
    self.rank += 100000 // self.rank
    if self.rank == 0:
      self.rank = 100

  def down(self):
    # TODO:
    # [x == 1/2*y - 1/2*sqrt(y^2 - 400), x == 1/2*y + 1/2*sqrt(y^2 - 400)]
    self.rank -= 100000 // self.rank

  def info(self):
    # CUSTOMABLE
    singer, title = os.path.split(self.file)
    singer = os.path.split(singer)[1]
    title = os.path.splitext(title)[0]
    return '%s - %s' % (singer, title)

  def toString(self):
    '''返回文本表示，用于保存到文件'''
    return '%s\x00%s\x00%s' % (self.file, self.rank, self.playedTimes)

class playlist:
  def __init__(self):
    if os.path.isfile(config['playlist']):
      self.load()
    else:
      self.loadFromMocp()

  def load(self):
    '''载入播放列表'''
    # 本来是想用 pickle 的，后来发现 pickle 有时不能跨程序使用
    # 这样也避免了导出问题
    self.songs = []
    for i in open(config['playlist']):
      i = i.split('\x00')
      self.songs.append(song(i[0], int(i[1]), int(i[2])))
    self.points = sum([x.rank for x in self.songs])

  def choose(self):
    '''选取一首歌'''
    r = random.randrange(self.points)
    s = 0
    for i in self.songs:
      s += i.rank
      if r < s:
        if not os.path.isfile(i.file):
          self.songs.remove(i)
          return self.choose()
        self.current = i
        i.playedTimes += 1
        return i
    raise RuntimeError('选歌出错！从总分 %d 中选取 %d 所在的歌曲时没有找到。'
        % (self.points, r))

  def rank(self, behaviour):
    '''增加当前歌曲的分数'''
    try:
      if behaviour == 'up':
        self.current.up()
        info('给 %s 加分了。' % self.current.info())
      elif behaviour == 'down':
        self.current.down()
        info('给 %s 降分了。' % self.current.info())
      else:
        raise ValueError('behaviour 必须为 “up” 或者 “down”。')
      self.save()
      return True
    except AttributeError:
      info('没有当前播放歌曲，无法调整歌曲评分。')
      return False

  def refresh(self):
    '''重新载入播放列表'''
    self.load()

  def save(self):
    '''保存播放列表'''
    with open(config['playlist'], 'w') as f:
      for s in self.songs:
        print(s.toString(), file=f)

  def add(self, file):
    '''向播放列表里添加一首歌'''
    if not os.path.isfile(file):
      info('%s 不存在，因此没有被导入。' % file)
      return False
    file = os.path.abspath(file)
    if file not in self:
      self.songs.append(song(file, rank=self.points // len(self.songs)))
      self.save()
      return True
    else:
      info('%s 已经存在于播放列表中了。' % file)
      return False

  def __contains__(self, file):
    '''file 应当是绝对路径'''
    for i in self.songs:
      if file == i.file:
        return True
    return False

  def loadFromMocp(self):
    '''从 mocp 的播放列表中载入'''
    pl = []
    info('从 mocp 的播放列表导入...')
    for l in open(config['mocpPlaylistFile']):
      l = l.strip()
      if l.startswith('#'):
        continue
      if os.path.isfile(l):
        pl.append(song(l))
      else:
        info("'%s' 不存在，因此没有被导入。" % l)
    self.songs = pl
    self.points = sum([x.rank for x in self.songs])

class server:
  def __init__(self):
    self.socket = socket_s(config['socket'], force=True)
    if config['useNotify']:
      self.notify = notify('xmocp 服务器开始运行。')
      if config['notifyOnStartup']:
        self.notify.show()
    else:
      self.notify = None
    self.playlist = playlist()
    configMocp()
    try:
      self.player = player()
    except player.ConnectionFail:
      info('mocp 没有运行，现在将运行它。')
      try:
        status = os.system('mocp -S')
        if status:
          fatal('mocp 返回错误号 %d！' % status)
          sys.exit(MocpError)
        self.player = player()
      except player.ConnectionFail:
        fatal('运行 mocp 失败！')
    self.run()

  def run(self):
    self.running = True
    if self.player.getState() == STATE_STOP:
      self.next()
    try:
      while self.running:
        self.socket.accept()
        cmd = self.socket.recv(int)
        if cmd == CMD_NEXT:
          self.next()
        elif cmd == CMD_EXIT:
          self.exit()
        elif cmd == CMD_SOFT_NEXT:
          if self.player.getState() == STATE_STOP:
            self.next()
        elif cmd == CMD_UP:
          self.playlist.rank('up')
        elif cmd == CMD_DOWN:
          self.playlist.rank('down')
        elif cmd == CMD_QUIT:
          self.quit()
        elif cmd == CMD_PL_REFRESH:
          self.playlist.refresh()
          info('播放列表已更新。')
        elif cmd == CMD_PING:
          pass
        else:
          info('收到未知信号 %d。' % cmd)
    except KeyboardInterrupt:
      info('退出。')
    except socket.error as e:
      if e.errno == 32:
        fatal('到 mocp 的连接已经中断。')

  def next(self):
    try:
      self.play(self.playlist.choose())
    except RuntimeError:
      self.next()

  def play(self, aSong):
    self.current = aSong
    if self.notify:
      self.notify.update('播放 %s' % aSong.info())
    info('播放 %s' % aSong.info())
    self.player.play(aSong.file)
    # s = path(aSong.file)
    # l = s.parent().join(s.rootname+'.lrc')
    # print(l)
    # if l.exists():
    #   pid = os.fork()
    #   if pid == 0:
    #     os.execlp('lrc.py', 'lrc.py', str(l))
    # else:
    #   print('没有找到 %s 的歌词文件。' % aSong.info())

  def exit(self):
    info('收到退出信号，服务器关闭。')
    # 这里用 sys.exit 会使主程序退出，这不一定是希望的
    self.running = False

  def quit(self):
    '''退出本程序的同时关闭 mocp'''
    info('关闭 mocp。')
    self.player.shutdown()
    self.exit()

def configMocp():
  '''修改 mocp 的配置文件'''
  file = config['mocpConfig']
  conf = None
  with open(file) as f:
    count = 0
    for i in f:
      i = i.strip()
      if i.startswith('OnStop'):
        conf = i
        break
      count += 1

  self = os.path.abspath(sys.argv[0])
  # 这里需要最后的 '\n'
  selfconf = '# This line was added by `xmcop\'\nOnStop = "%s"\n' % self
  if not conf or conf[conf.find('=')+1:].strip(' "') != self:
    c = open(file).readlines()
    if conf:
      c[count] = '#' + c[count]
    c.append(selfconf)
    open(file, 'w').writelines(c)
    info('已经自动更新 mocp 配置文件')

def addSong(fd):
  pl = playlist()
  for l in fd:
    l = l.strip()
    pl.add(l)
  # 通知服务器歌曲列表已更新
  try:
    clientSay(CMD_PL_REFRESH)
  except socket.error:
    pass

def clientSay(cmd):
  '''向服务器发消息'''
  try:
    s = socket_c(config['socket'])
    s.send(cmd)
    return True
  except socket.error as e:
    if e.errno in (111,):
      return False
  finally:
    try:
      s.close()
    except NameError:
      pass

def main():
  import getopt
  if len(sys.argv) == 1:
    if not clientSay(CMD_PING):
      info('xmocp 服务器未运行。')
      usage()
      sys.exit(NoAction)
    else:
      clientSay(CMD_SOFT_NEXT)
      sys.exit()

  try:
    optlist, args = getopt.gnu_getopt(sys.argv[1:], 'a:npudqxhv',
        ['add=', 'play', 'help', 'up', 'down', 'exit', 'quit', 'version'])
  except getopt.GetoptError:
    usage()
    sys.exit(GetoptError)

  for opt, arg in optlist:
    if opt in ('-h', '--help'):
      usage()
      sys.exit()
    elif opt in ('-v', '--version'):
      print('xmocp %s' % version)
    elif opt in ('-a', '--add'):
      if arg == '-':
        fd = sys.stdin
      else:
        try:
          fd = open(arg)
        except IOError as e:
          fatal('%d -- %s！' % (e.errno, e.strerror))
          sys.exit(MyIOError)
      addSong(fd)
      fd.close()
      sys.exit()
    elif opt in ('-q', '--quit'):
      if not clientSay(CMD_QUIT):
        info('xmocp 服务器未运行。')
        info('仍旧关闭 mocp。')
        if os.system('mocp -x') == 2:
          sys.exit(NoAction)
    elif opt in ('-x', '--exit'):
      if not clientSay(CMD_EXIT):
        info('xmocp 服务器未运行。')
        sys.exit(NoAction)
    elif opt in ('-n', '--next'):
      if not clientSay(CMD_NEXT):
        info('xmocp 服务器未运行。')
        sys.exit(NoAction)
    elif opt in ('-u', '--up'):
      if not clientSay(CMD_UP):
        info('xmocp 服务器未运行。')
        sys.exit(NoAction)
    elif opt in ('-d', '--down'):
      if not clientSay(CMD_DOWN):
        info('xmocp 服务器未运行。')
        sys.exit(NoAction)
    elif opt in ('-p', '--play'):
      if clientSay(CMD_PING):
        info('xmocp 服务器已经在运行。')
      else:
        if not os.fork():
          server()

def usage():
  print('''\t\txmocp --- 按喜好随机播放的 mocp！

选项：
  -a FILE                  向播放列表添加歌曲，若 FILE 为 -，从标准输入读取列表
      --add=FILE
  -p, --play               开始运行
  -n, --next               播放下一曲

  -u, --up                 增加当前歌曲的分数
  -d, --down               减少当前歌曲的分数

  -x, --exit               退出本程序
  -q, --quit               退出本程序，同时关闭 mocp
  -h, --help               显示这个帮助
  -v, --version            显示版本

作者：
  lilydjwg <missyou11@163.com>

版本：
  {version}
'''.format(version=version))

if __name__ == '__main__':
  lastModified = datetime.fromtimestamp(os.path.getmtime(sys.argv[0]))
  version = '%.1f.%d%02d%02d' % (ver, lastModified.year, lastModified.month, lastModified.day)
  main()

