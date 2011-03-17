#!/usr/bin/env python3
# vim:fileencoding=utf-8

class MPlayer:
  def docmd(self, cmd):
    if not os.path.exists(self.fifo):
      raise MplayerError('FIFO 文件丢失')

    # 任何命令都会导致已暂停者继续播放
    self.playing = True
    if not cmd.endswith('\n'):
      cmd += '\n'
    f = open(self.fifo, 'w')
    f.write(cmd)
    f.close()
    time.sleep(0.2)
    return self.sub.output()

