#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''
QQ群邮件
'''

import lxml.html

class GroupMailHeader:
  '''
  群邮件元信息

  属性列表：
    mailid
    unread: bool
    sender
    gid
    gname:  群名
    subject
    summary
    date
  '''
  def __init__(self, table):
    mail = table.cssselect('input[name="mailid"]')[0]
    self.mailid = mail.get('value')
    unread = mail.get('unread')
    if unread == 'false':
      self.unread = False
    else:
      self.unread = True
    self.sender = mail.get('fa')
    self.gid = mail.get('gid')
    self.gname = mail.get('fn')
    subject = table.cssselect('u')[0]
    self.subject = subject.text
    self.summary = subject.getnext().text.strip()
    self.date = table.cssselect('td.dt > div')[0].text.strip()

  def __repr__(self):
    return '<GroupMailHeader: {self.subject} from {self.gname}>'.format(self=self)

  def __str__(self):
    return '{self.gname}：{self.subject}，{self.date}'.format(self=self)

  def geturl(self):
    '''返回相对于 /cgi-bin/ 的路径，其中 sid 部分使用 %s 代替'''
    return 'readmail?folderid=8&t=readmail_group&mailid={self.mailid}&mode=pre&maxage=600&base=12&ver=10646&sid=%s'.format(self=self)

class GroupMail:
  '''
  群邮件中的一个帖子

  属性列表：
    sender: 发送者姓名
    senderid: QQ 号
    sendermail: 邮箱
    date
    time
  '''
  def __init__(self, div):
    info = div.cssselect('div.qm_dispname')[0]
    sender = info.cssselect('a')[0]
    self.sender = sender.get('n')
    self.senderid = sender.get('u')
    self.sendermail = sender.get('e')
    span = info.cssselect('span.normal')[0]
    self.date = span.text
    self.time = span[-1].tail
    
    content = div.cssselect('div.qm_converstaion_body')[0]
    self.content = content.xpath('string()').strip()

    # TODO 附件

  def __repr__(self):
    return '<%s 的帖子>' % self.sender

  def __str__(self):
    return '%s:\n\t%s' % (self.sender, self.content.replace('\n', '\n\t'))

def parseGroupMails(page):
  doc = lxml.html.fromstring(page)
  table_of_mails = doc.cssselect('form#frm > div.toarea > table')
  mails = []
  for table in table_of_mails:
    mails.append(GroupMailHeader(table))
  return mails

def parseSingleGroupMail(page):
  doc = lxml.html.fromstring(page)
  allmails = doc.cssselect('div.qm_converstaion_bd')
  mails = []
  for div in allmails:
    mails.append(GroupMail(div))
  mails.reverse()
  return mails
