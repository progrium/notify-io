import wsgiref.handlers
import hashlib, time

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

from main import Account, Notification

class DashboardHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/')
        account = Account.all().filter('user =', user).get()
        if not account:
            account = Account()
            account.set_hash_and_key()
            account.put()
        self.response.out.write(template.render('templates/dashboard_home.html', locals()))

class SettingsHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/')
        account = Account.all().filter('user =', user).get()
        self.response.out.write(template.render('templates/dashboard_settings.html', locals()))

class HistoryHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/')
        account = Account.all().filter('user =', user).get()
        notifications = Notification.all().filter('hash =', account.hash)
        self.response.out.write(template.render('templates/dashboard_history.html', locals()))

class SourcesHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/')
        self.response.out.write(template.render('templates/dashboard_sources.html', locals()))

class NotifiersHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/')
        self.response.out.write(template.render('templates/dashboard_notifiers.html', locals()))

def main():
    application = webapp.WSGIApplication([
        ('/dashboard', DashboardHandler), 
        ('/dashboard/settings', SettingsHandler),
        ('/dashboard/history', HistoryHandler),
        ('/dashboard/sources', SourcesHandler),
        ('/dashboard/notifiers', NotifiersHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()