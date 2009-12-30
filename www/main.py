import wsgiref.handlers
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

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

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class Account(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hash = db.StringProperty()
    api_key = db.StringProperty()
    source_enabled = db.BooleanProperty()
    source_name = db.StringProperty()
    source_icon = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)

    #def __init__(self, *args, **kwargs):
    #    super(Account, self).__init__(*args, **kwargs)
    
    @classmethod
    def get_by_user(cls, user):
        return cls.all().filter('user =', user).get()
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()

    def set_hash_and_key(self):
        self.hash = hashlib.md5(self.user.email()).hexdigest()
        self.api_key = ''.join([baseN(abs(hash(time.time())), 36), baseN(abs(hash(self.hash)), 36)])

class Channel(db.Model):
    target = db.ReferenceProperty(Account, required=True, collection_name='channels_as_target')
    source = db.ReferenceProperty(Account, required=True, collection_name='channels_as_source')
    status = db.StringProperty(required=True, default='pending')
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def get_all_by_target(cls, account):
        return cls.all().filter('target =', account)

    @classmethod
    def get_all_by_source(cls, account):
        return cls.all().filter('source =', account)
    
    @classmethod
    def get_by_source_and_target(cls, source, target):
        return cls.all().filter('source =', source).filter('target =', target).get()
    
    def delete(self):
        notices = Notification.all().filter('channel =', self)
        for n in notices:
            n.channel = None
            n.put()
        super(Channel, self).delete()
    
    def get_approval_notice(self):
        notice = Notification(channel=self, target=self.target, text="%s wants to send you notifications. Click here to approve/deny this request." % self.source.source_name)
        notice.title = "New Notification Source"
        notice.link = "http://%s/dashboard/sources" % WWW_HOST
        notice.icon = self.source.source_icon
        notice.sticky = 'true'
        return notice
        

class Notification(db.Model):
    channel = db.ReferenceProperty(Channel)
    target = db.ReferenceProperty(Account, collection_name='target_notifications')
    source = db.ReferenceProperty(Account, collection_name='source_notifications')
    
    title = db.StringProperty()
    text = db.TextProperty(required=True)
    link = db.StringProperty()
    icon = db.StringProperty()
    sticky = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    
    def __init__(self, *args, **kwargs):
        channel = kwargs.get('channel')
        if channel and isinstance(channel, Channel):
            kwargs['source'] = channel.source
            kwargs['target'] = channel.target
        super(Notification, self).__init__(*args, **kwargs) 
    
    def to_json(self):
        o = {'text': self.text}
        for arg in ['title', 'link', 'icon', 'sticky']:
            value = getattr(self, arg)
            if value:
                o[arg] = value
        o['source'] = self.source.source_name
        return simplejson.dumps(o)

class MainHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            logout_url = users.create_logout_url('/')
        else:
            login_url = users.create_login_url('/dashboard')
        self.response.out.write(template.render('templates/main.html', locals()))

class NotificationHandler(webapp.RequestHandler):
    def post(self): 
        target = Account.all().filter('hash =', self.request.get('hash')).get()
        source = Account.all().filter('api_key =', self.request.get('api_key')).get()
        replay = self.request.get('replay', None)
        if replay:
            self.replay(replay, target, source)
        else:
            self.notify(target, source)
    
    def replay(self, replay, target, source):
        notice = Notification.get_by_id(int(replay))
        channel = notice.channel
        # Can only replay if hash == notification target AND (api_key == notification source OR notification target)
        authz = channel.target.key() == target.key() and (channel.source.key() == source.key() or source.key() == channel.target.key())
        if notice and channel.status == 'enabled' and authz:
            self.response.out.write(notice.to_json())
        else:
            self.error(404)
    
    def notify(self, target, source):
        channel = Channel.all().filter('target =', target).filter('source =', source).get()
        approval_notice = None
        if not channel and source and target:
            channel = Channel(target=target, source=source)
            channel.put()
            approval_notice = channel.get_approval_notice()
        if channel:
            notice = Notification(channel=channel, text=self.request.get('text'), icon=source.source_icon)
            for arg in ['title', 'link', 'icon', 'sticky']:
                value = self.request.get(arg, None)
                if value:
                    setattr(notice, arg, value)
            notice.put()
            if channel.status == 'enabled':
                self.response.out.write(notice.to_json())
            elif channel.status == 'pending':
                self.response.set_status(202)
                if approval_notice:
                    self.response.out.write(approval_notice.to_json())
                else:
                    self.response.out.write("202 Pending approval")
            elif channel.status == 'disabled':
                self.response.set_status(202)
                self.response.out.write("202 Accepted but disabled")
        else:
            self.error(404)
            self.response.out.write("404 Target or source not found")

class DownloadHandler(webapp.RequestHandler):
    @login_required
    def get(self):
        user = users.get_current_user()
        account = Account.all().filter('user =', user).get()
        host = API_HOST
        hash = account.hash
        api_key = account.api_key
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.headers['Content-disposition'] = 'attachment; filename=config.ListenURL'
        self.response.out.write("http://%s/v1/listen/%s?api_key=%s" % (host, hash, api_key))

class ListenAuthHandler(webapp.RequestHandler):
    def get(self):
        api_key = self.request.get('api_key')
        userhash = self.request.get('hash')
        account = Account.all().filter('hash =', userhash).filter('api_key =', api_key).get()
        if account:
            self.response.out.write("ok")
        else:
            self.error(403)

class IntroHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        logout_url = users.create_logout_url('/getstarted')
        if not user:
            login_url = users.create_login_url('/getstarted')
        self.response.out.write(template.render('templates/getstarted.html', locals()))
        
class AvailableSourcesHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render('templates/availablesources.html', locals()))

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/notification', NotificationHandler), 
        ('/config.ListenURL', DownloadHandler),
        ('/auth', ListenAuthHandler),
        ('/getstarted', IntroHandler),
        ('/availablesources', AvailableSourcesHandler)
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
