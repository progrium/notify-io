import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import mail, users, urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

import logging

from config import WWW_HOST
import outlet_types

def baseN(num,b=36,numerals="0123456789abcdefghijklmnopqrstuvwxyz"): 
    return ((num == 0) and  "0" ) or (baseN(num // b, b).lstrip("0") + numerals[num % b])

class Account(db.Model):
    user = db.UserProperty(auto_current_user_add=True)
    hash = db.StringProperty()
    hashes = db.StringListProperty()
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

    def source_or_default_icon(self):
        return self.source_icon or 'http://%s/favicon.ico' % WWW_HOST

    def get_default_outlet(self):
        return Outlet.all().filter('target =', self).filter('type_name =', 'DesktopNotifier').order('-created').get()

    def set_hash_and_key(self):
        self.hash = hashlib.md5(self.user.email().lower()).hexdigest()
        d = hashlib.md5(str(time.time()) + self.hash).hexdigest()
        self.api_key = '-'.join([d[0:6], d[8:14], d[16:22], d[24:30]])

class Email(db.Model):
    account = db.ReferenceProperty(Account, required=True)
    email = db.StringProperty(required=True)
    pending_token = db.StringProperty()
    
    def __init__(self, *args, **kwargs):
        kwargs['pending_token'] = kwargs.get('pending_token', hashlib.sha1(str(time.time())).hexdigest())
        super(Email, self).__init__(*args, **kwargs)
    
    def hash(self):
        return hashlib.md5(self.email).hexdigest()
    
    def send_activation_email(self):
        if self.pending_token:
            mail.send_mail(
                sender="Notify.io <no-reply@notify-io.appspotmail.com>",
                to=self.email,
                subject="Activate additional email address",
                body="Hello,\n\nClick on this link to activate this email address:\nhttp://%s/settings/activate/%s" % (WWW_HOST, self.pending_token))
        else:
            raise Exception("pending_token is not set")
    
    @classmethod
    def activate(cls, token):
        email = cls.all().filter('pending_token =', token).get()
        if email:
            email.account.hashes.append(email.hash())
            email.account.put()
            email.pending_token = None
            email.put()
    
    @classmethod
    def find_existing(cls, email):
        hash = hashlib.md5(email).hexdigest()
        found = Account.all().filter('hash =', hash).get()
        if not found:
            found = Account.all().filter('hashes =', hash).get()
        if not found:
            found = Email.all().filter('email =', email).get()
        return found

class Outlet(db.Model):
    hash = db.StringProperty()
    target = db.ReferenceProperty(Account, required=True)
    type_name = db.StringProperty(required=True)
    name = db.StringProperty()
    params = db.StringProperty()
    
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    

    def __init__(self, *args, **kwargs):
        kwargs['hash'] = kwargs.get('hash', hashlib.sha1(str(time.time())).hexdigest())
        super(Outlet, self).__init__(*args, **kwargs)
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()
    
    def delete(self):
        for channel in Channel.get_all_by_target(self.target):
            channel.outlet = None
            channel.put()
        super(Outlet, self).delete()
    
    def type(self):
        return outlet_types.get(self.type_name)
    
    def is_push(self):
        return self.type().push
    
    def push_destination(self):
        if self.is_push():
            return [self.type().fields[0], self.get_param(self.type().fields[0])]
        else:
            return None
    
    def get_param(self, key):
        return simplejson.loads(self.params)[key]
    
    def set_params(self, input):
        params = dict()
        for f in self.type().fields:
            params[f] = input.get(f)
        self._tmp_params = params
        self.params = simplejson.dumps(params)
    
    def set_name(self, name=None):
        if not name:
            name = self.type().default_name(self._tmp_params)
        self.name = name
    
    def setup(self, params):
        self.set_params(params)
        self.set_name()
        self.type().setup(self)


class Channel(db.Model):
    target = db.ReferenceProperty(Account, required=True, collection_name='channels_as_target')
    source = db.ReferenceProperty(Account, required=True, collection_name='channels_as_source')
    outlet = db.ReferenceProperty(Outlet)
    count = db.IntegerProperty(default=0)

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
        notice.link = "http://%s/sources" % WWW_HOST
        notice.icon = self.source.source_icon
        notice.sticky = 'true'
        return notice
        

class Notification(db.Model):
    hash = db.StringProperty()
    channel = db.ReferenceProperty(Channel)
    target = db.ReferenceProperty(Account, collection_name='target_notifications')
    source = db.ReferenceProperty(Account, collection_name='source_notifications')
    
    title = db.StringProperty()
    text = db.StringProperty(multiline=True, required=True)
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
    
    def dispatch(self):
        if self.channel.outlet:
            return str(self.channel.outlet.type().dispatch(self))
        else:
            return ''
    
    @classmethod
    def get_by_hash(cls, hash):
        return cls.all().filter('hash = ', hash).get()

    @classmethod
    def get_history_by_target(cls, target):
        return cls.all().filter('target =', target).order('-created')
    
    def icon_with_default(self):
        return self.icon or self.source.source_or_default_icon()
    
    def to_dict(self):
        o = {'text': self.text.replace('\r\n', '\n')}
        for arg in ['title', 'link', 'icon', 'sticky']:
            value = getattr(self, arg)
            if value:
                o[arg] = value
        o['source'] = self.source.source_name
        return o
        
    def to_json(self):
        return simplejson.dumps(self.to_dict())
