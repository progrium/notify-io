import wsgiref.handlers
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel
from app import API_HOST, API_VERSION, RequestHandler


class MainHandler(RequestHandler):
    def get(self):
        self.render('templates/main.html', locals())

class DownloadHandler(RequestHandler):
    @login_required
    def get(self):
        host = API_HOST
        hash = self.account.hash
        api_key = self.account.api_key
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.headers['Content-disposition'] = 'attachment; filename=config.ListenURL'
        self.response.out.write("http://%s/v1/listen/%s?api_key=%s" % (host, hash, api_key))


class GetStartedHandler(RequestHandler):
    def get(self):
        self.render('templates/getstarted.html', locals())
        
class SourcesAvailableHandler(RequestHandler):
    def get(self):
        self.render('templates/sources_available.html', locals())

class SettingsHandler(RequestHandler):
    @login_required
    def get(self):
        api_host = API_HOST
        api_version = API_VERSION
        pending_channels = Channel.get_all_by_target(self.account).filter('status =', 'pending')
        self.render('templates/settings.html', locals())
    
    def post(self):
        if self.request.get('source_enabled', None):
            self.account.source_enabled = True
            self.account.source_name = self.request.get('source_name', None)
            self.account.source_icon = self.request.get('source_icon', None)
        else:
            self.account.source_enabled = False
        self.account.put()
        self.redirect('/dashboard/settings')

class HistoryHandler(RequestHandler):
    @login_required
    def get(self):
        api_host = API_HOST
        api_version = API_VERSION
        pending_channels = Channel.get_all_by_target(self.account).filter('status =', 'pending')
        notifications = Notification.all().filter('target =', self.account).order('-created').fetch(1000)
        self.render('templates/history.html', locals())

class SourcesHandler(RequestHandler):
    @login_required
    def get(self):
        pending_channels = Channel.get_all_by_target(self.account).filter('status =', 'pending')
        enabled_channels = Channel.get_all_by_target(self.account).filter('status =', 'enabled')
        self.render('templates/sources.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'approve':
            source = Account.get_by_hash(self.request.get('source'))
            channel = Channel.get_by_source_and_target(source, self.account)
            channel.status = 'enabled'
            channel.put()
        if action == 'disable':
            source = Account.get_by_hash(self.request.get('source'))
            channel = Channel.get_by_source_and_target(source, self.account)
            channel.status = 'disabled'
        self.redirect('/dashboard/sources')

class OutletsHandler(RequestHandler):
    @login_required
    def get(self):
        pending_channels = Channel.get_all_by_target(self.account).filter('status =', 'pending')
        self.render('templates/outlets.html', locals())


def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/config.ListenURL', DownloadHandler),
        ('/getstarted', GetStartedHandler),
        ('/sources/available', SourcesAvailableHandler),
        ('/settings', SettingsHandler),
        ('/history', HistoryHandler),
        ('/sources', SourcesHandler),
        ('/outlets', OutletsHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
