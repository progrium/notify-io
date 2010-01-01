import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

def baseN(num,b,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class Account(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hash = db.StringProperty()
    api_key = db.StringProperty()
    source_enabled = db.BooleanProperty()
    source_name = db.StringProperty()
    source_url = db.StringProperty()
    source_icon = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    started = db.BooleanProperty(default=False)

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
    hash = db.StringProperty()
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
        kwargs['hash'] = kwargs.get('hash', hashlib.sha1(str(time.time())).hexdigest())
        super(Notification, self).__init__(*args, **kwargs) 
    
    def to_json(self):
        o = {'text': self.text}
        for arg in ['title', 'link', 'icon', 'sticky']:
            value = getattr(self, arg)
            if value:
                o[arg] = value
        o['source'] = self.source.source_name
        return simplejson.dumps(o)
