import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users

from models import Account, Channel, Outlet, Notification
from config import API_HOST, WWW_HOST, API_VERSION 

register = webapp.template.create_template_register()

@register.filter
def replace(value, arg):
    old, new = arg.split(',')
    return value.replace(old, new)

@register.filter
def shortago(value):
    value = value.replace(' hours', 'h').replace(' hour', 'h') \
                .replace(' minutes', 'm').replace(' minute', 'm') \
                .replace(' days', 'd').replace(' day', 'd')
    return '%s ago' % value

class RequestHandler(webapp.RequestHandler):
    def initialize(self, request, response):
        super(RequestHandler, self).initialize(request, response)
        self.user = users.get_current_user()
        if self.user:
            self.login_url = None
            self.logout_url = users.create_logout_url('/')
            self.account = Account.all().filter('user =', self.user).get()
            if not self.account:
                # Set up a Notify.io account
                
                self.account = Account()
                self.account.set_hash_and_key()
                self.account.source_name = self.user.nick() # More useful default than None
                self.account.put()
                
                # Create default Desktop Notifier
                o = Outlet(target=self.account, type_name='DesktopNotifier')
                o.set_name("Default Desktop Notifier")
                o.put()
        else:
            self.logout_url = None
            self.account = None
            self.login_url = users.create_login_url(request.path)
        
        # Hide the Get Started tip
        if request.query_string == 'hide':
            self.account.started = True
            self.account.put()
    
    def render(self, template_path, locals):
        locals.update({
            'user': self.user,
            'logout_url': self.logout_url,
            'login_url': self.login_url,
            'account': self.account,
            'api_host': API_HOST,
            'api_version': API_VERSION,
            'www_host': WWW_HOST,
        })
        self.response.out.write(template.render(template_path, locals))

class DashboardHandler(RequestHandler):
    def render(self, template_path, locals):
        locals['pending_channels'] = Channel.get_all_by_target(self.account).filter('status =', 'pending').fetch(10)
        locals['recent_notifications'] = Notification.get_history_by_target(self.account).fetch(3)
        super(DashboardHandler, self).render(template_path, locals)