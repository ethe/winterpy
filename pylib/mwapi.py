#!/usr/bin/env python3
# vim:fileencoding=utf-8

'''wrapper of MediaWiki API'''

from httpsession import Session
import json

class Site(Session):
  def __init__(self, apiurl, username=None, password=None, **kwargs):
    super().__init__(**kwargs)
    self.apiurl = apiurl
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
    return ans

  def request(self, data, **kwargs):
    data['format'] = 'json'
    ans = super().request(self.apiurl, data, **kwargs).read().decode('utf-8')
    return json.loads(ans)

  def __getitem__(self, title):
    return self.getPage(title, redirect=True)

  def getPage(self, title, redirect=False):
    data = {
      'action': 'query',
      'titles': title,
    }
    if redirect:
      data['redirects'] = ''
    ans = self.request(data)
    return Page(ans['query'], self)

class Page:
  def __init__(self, pageinfo, site):
    self.site = site
    if pageinfo['redirects']:
      self.redirectedfrom = pageinfo['redirects'][0]['from']
    if pageinfo['normalized']:
      self.normalizedto = pageinfo['normalized'][0]['to']
    page = tuple(pageinfo['pages'].values())[0]
    self.title = page['title']
    self.namespace = page['ns']
    self.pageid = page['pageid']

  @property
  def content(self):
    data = {
      'action': 'query',
      'titles': self.title,
      'prop': 'revisions',
      'rvprop': 'content',
    }
    ans = self.site.request(data)
    page = tuple(ans['query']['pages'].values())[0]
    return tuple(page['revisions'][0].values())[0]

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
