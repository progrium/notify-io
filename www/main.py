import wsgiref.handlers
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel, Outlet
from app import RequestHandler, DashboardHandler
from config import API_HOST, API_VERSION
import outlet_types

class MainHandler(RequestHandler):
    def get(self):
        self.render('templates/main.html', locals())

class GetStartedHandler(RequestHandler):
    def get(self):
        start_outlet = self.account.get_default_outlet()
        self.render('templates/getstarted.html', locals())
        
class SourcesAvailableHandler(RequestHandler):
    def get(self):
        self.render('templates/sources_available.html', locals())

class SettingsHandler(DashboardHandler):
    @login_required
    def get(self):
        api_host = API_HOST
        api_version = API_VERSION
        self.render('templates/settings.html', locals())
    
    def post(self):
        if self.request.get('source_enabled', None):
            self.account.source_enabled = True
            self.account.source_name = self.request.get('source_name', None)
            self.account.source_url = self.request.get('source_url', None)
            self.account.source_icon = self.request.get('source_icon', None)
        else:
            self.account.source_enabled = False
        self.account.put()
        self.redirect('/settings')

class HistoryHandler(DashboardHandler):
    @login_required
    def get(self):
        api_host = API_HOST
        api_version = API_VERSION
        notifications = Notification.all().filter('target =', self.account).order('-created').fetch(1000)
        self.render('templates/history.html', locals())

class SourcesHandler(DashboardHandler):
    @login_required
    def get(self):
        outlets = Outlet.all().filter('target =', self.account)
        enabled_channels = Channel.get_all_by_target(self.account).filter('status =', 'enabled')
        self.render('templates/sources.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'approve':
            source = Account.get_by_hash(self.request.get('source'))
            channel = Channel.get_by_source_and_target(source, self.account)
            channel.status = 'enabled'
            channel.put()
        elif action == 'disable':
            source = Account.get_by_hash(self.request.get('source'))
            channel = Channel.get_by_source_and_target(source, self.account)
            channel.status = 'disabled'
        elif action == 'route':
            source = Account.get_by_hash(self.request.get('source'))
            channel = Channel.get_by_source_and_target(source, self.account)
            outlet = Outlet.get_by_hash(self.request.get('outlet'))
            channel.outlet = outlet
            channel.put()
        self.redirect('/sources')

class OutletsHandler(DashboardHandler):
    @login_required
    def get(self):
        if self.request.path.endswith('.ListenURL'):
            filename = self.request.path.split('/')[-1]
            outlet = filename.split('.')[0]
            
            self.account.started = True
            self.account.put()

            host = API_HOST
            hash = self.account.hash
            api_key = self.account.api_key
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.headers['Content-disposition'] = 'attachment; filename=%s.ListenURL' % outlet
            self.response.out.write("http://%s/v1/listen/%s\n" % (host, outlet))
        else:
            types = outlet_types.all
            outlets = Outlet.all().filter('target =', self.account)
            self.render('templates/outlets.html', locals())
    
    def post(self):
        action = self.request.get('action')
        if action == 'add':
            o = Outlet(target=self.account, type_name=self.request.get('type'))
            o.set_params(self.request.POST)
            o.set_name()
            o.put()
        elif action == 'remove':
            o = Outlet.get_by_hash(self.request.get('outlet'))
            o.delete()
        self.redirect('/outlets')

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/getstarted', GetStartedHandler),
        ('/sources/available', SourcesAvailableHandler),
        ('/settings', SettingsHandler),
        ('/history', HistoryHandler),
        ('/sources', SourcesHandler),
        ('/outlets.*', OutletsHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
