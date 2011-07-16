#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''wrapper of MediaWiki API'''

from httpsession import Session
import json
import logging

logger = logging.getLogger(__name__)

class Site(Session):
  def __init__(self, apiurl, username=None, password=None, **kwargs):
    super().__init__(**kwargs)
    self.apiurl = apiurl
    self.loggedin = False
    if username is not None:
      self.login(username, password)

  def login(self, username, password, domain=None):
    data = {
      'action': 'login',
      'lgname': username,
      'lgpassword': password,
    }
    if domain is not None:
      data['lgdomain'] = domain
    ans = self.request(data)
    data['lgtoken'] = ans['login']['token']
    ans = self.request(data)
    if ans['login']['result'] != 'Success':
      raise AuthError(ans['login']['result'], ans)
    self.loggedin = True
    return ans

  def logout(self):
    data = {
      'action': 'logout',
    }
    self.request(data)
    self.loggedin = False

  def request(self, data, **kwargs):
    data['format'] = 'json'
    logger.debug('> %r', data)
    ans = super().request(self.apiurl, data, **kwargs).read().decode('utf-8')
    ans = json.loads(ans)
    logger.debug('< %r', ans)
    return ans

  def __getitem__(self, title):
    return self.getPage(title, redirect=True)

  def getPage(self, title, redirect=False):
    data = {
      'action': 'query',
      'titles': title,
    }
    if redirect:
      data['redirects'] = '1'
    ans = self.request(data)
    return Page(ans['query'], self)

  def getEditToken(self, title):
    return self.getToken('edit', title)

  def getToken(self, kind, title):
    data = {
      'action': 'query',
      'prop': 'info',
      'intoken': kind,
      'titles': title
    }
    ans = self.request(data)
    if 'warnings' in ans:
      warning = tuple(ans['warnings']['info'].values())[0]
      if warning.find('not allowed') > 0:
        raise AuthError(warning, ans)
      else:
        raise MediaWikiError(warning, ans)
    page = tuple(ans['query']['pages'].values())[0]
    return page['%stoken' % kind]

class Page:
  def __init__(self, pageinfo, site):
    self.site = site
    if 'redirects' in pageinfo:
      self.redirectedfrom = pageinfo['redirects'][0]['from']
    else:
      self.redirectedfrom = None
    if 'normalized' in pageinfo:
      self.normalizedto = pageinfo['normalized'][0]['to']
    else:
      self.normalizedto = None
    page = tuple(pageinfo['pages'].values())[0]
    self.title = page['title']
    self.namespace = page['ns']
    self.pageid = page['pageid']
    self.timestamp = None

  @property
  def content(self):
    data = {
      'action': 'query',
      'titles': self.title,
      'prop': 'revisions',
      'rvprop': 'content|timestamp',

    }
    ans = self.site.request(data)
    page = tuple(ans['query']['pages'].values())[0]
    self.timestamp = page['revisions'][0]['timestamp']
    return page['revisions'][0]['*']

  @content.setter
  def content(self, text):
    self.edit(text)

  def edit(self, text, summary=None, minor=False):
    data = {
      'action': 'edit',
      'title': self.title,
      'text': text,
      'token': self.site.getEditToken(self.title),
    }
    if self.timestamp is not None:
      data['basetimestamp'] = self.timestamp
    if summary is not None:
      data['summary'] = summary
    if minor:
      data['minor'] = '1'
    else:
      data['notminor'] = '1'
    ans = self.site.request(data)
    if 'error' in ans:
      raise MediaWikiError(ans['error']['info'], ans)
    elif 'edit' not in ans or ans['edit']['result'] != 'Success':
      raise MediaWikiError('unknown error', ans)
    return ans['edit']

  def __repr__(self):
    return '<Page: %s from %s/>' % (self.title, self.site.apiurl.rsplit('/', 1)[0])

class MediaWikiError(Exception):
  def __init__(self, desc, data):
    self.desc = desc
    self.data = data

  def __repr__(self):
    return '<%s: %s>' % (self.__class__, self.desc)
  
  def __str__(self):
    return self.desc

class AuthError(MediaWikiError): pass
