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
    notifier_name = db.StringProperty()
    notifier_icon = db.BlobProperty()

    def __init__(self, *args, **kwargs):
        user = kwargs.get('user')
        if user:
            kwargs['hash'] = hashlib.md5(user.email()).hexdigest()
        kwargs['api_key'] = kwargs.get('api_key', baseN(abs(hash(time.time())), 36))
        super(Account, self).__init__(*args, **kwargs)


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

def main():
    application = webapp.WSGIApplication([('/', MainHandler), ('/log', LogHandler), ('/download/notifyio-client.py', DownloadHandler)], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
