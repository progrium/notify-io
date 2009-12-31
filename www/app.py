import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users

from models import Account

try:
    is_dev = os.environ['SERVER_SOFTWARE'].startswith('Dev')
except:
    is_dev = False

API_VERSION = 'v1'
if is_dev:
    API_HOST = 'localhost:8191'
    WWW_HOST = 'localhost:8091'
else:
    API_HOST = 'api.notify.io'
    WWW_HOST = 'www.notify.io'
    

class RequestHandler(webapp.RequestHandler):
    def initialize(self, request, response):
        super(RequestHandler, self).initialize(request, response)
        self.user = users.get_current_user()
        if self.user:
            self.login_url = None
            self.logout_url = users.create_logout_url('/')
            self.account = Account.all().filter('user =', self.user).get()
            if not self.account:
                account = Account()
                account.set_hash_and_key()
                account.put()
        else:
            self.logout_url = None
            self.account = None
            self.login_url = users.create_login_url(request.path)
    
    def render(self, template_path, locals):
        locals.update({
            'user': self.user,
            'logout_url': self.logout_url,
            'login_url': self.login_url,
            'account': self.account,
        })
        self.response.out.write(template.render(template_path, locals))