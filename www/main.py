import wsgiref.handlers
import hashlib, time

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class Notification(db.Model):
    hash = db.StringProperty(required=True)
    title = db.StringProperty()
    text = db.TextProperty(required=True)
    link = db.StringProperty()
    icon = db.StringProperty()
    sticky = db.BooleanProperty()

class Account(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hash = db.StringProperty()
    api_key = db.StringProperty()
    source_enabled = db.BooleanProperty()
    source_name = db.StringProperty()
    source_icon = db.StringProperty()

    #def __init__(self, *args, **kwargs):
    #    super(Account, self).__init__(*args, **kwargs)

    def set_hash_and_key(self):
        self.hash = hashlib.md5(self.user.email()).hexdigest()
        self.api_key = ''.join([baseN(abs(hash(time.time())), 36), baseN(abs(hash(self.hash)), 36)])

class MainHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.redirect('/dashboard')
            return
        else:
            login_url = users.create_login_url('/')
        self.response.out.write(template.render('templates/main.html', locals()))

class LogHandler(webapp.RequestHandler):
    def post(self):
        notice = Notification(hash=self.request.get('hash'), text=self.request.get('text'))
        for arg in ['text', 'link', 'icon', 'sticky']:
            value = self.request.get(arg, None)
            if value:
                setattr(notice, arg, value)
        notice.put()
        self.response.out.write("ok")

class DownloadHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        account = Account.all().filter('user =', user).get()
        host = 'api.notify.io'
        hash = account.hash
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(template.render('templates/client.py', locals()))

class ListenAuthHandler(webapp.RequestHandler):
    def get(self):
        api_key = self.request.get('api_key')
        userhash = self.request.get('hash')
        account = Account.all().filter('hash =', userhash).filter('api_key =', api_key).get()
        if account:
            self.response.out.write("ok")
        else:
            self.error(403)

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/log', LogHandler), 
        ('/download/notifyio-client.py', DownloadHandler),
        ('/auth', ListenAuthHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
