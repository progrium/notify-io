import wsgiref.handlers
import hashlib, time, os, re
import base64
import logging

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch, memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel
from config import API_HOST, API_VERSION
from app import RequestHandler

def strip_tags(value):
    return re.sub(r'<[^>]*?>', '', value or '')

class ReplayHandler(RequestHandler):
    def post(self, hash): 
        hash = hash.lower()
        notice = Notification.all().filter('hash =', hash).get()
        target = Account.all().filter('api_key =', self.request.get('api_key')).get()
        channel = notice.channel
        if notice and channel.status == 'enabled' and channel.target.key() == target.key():
            notice.dispatch()
            self.response.out.write("OK\n")
        else:
            self.error(404)


class NotifyHandler(RequestHandler):
    def post(self, hash): 
        hash = hash.lower()
        target = Account.all().filter('hash =', hash).get()
        if not target:
            target = Account.all().filter('hashes =', hash).get()
        source = Account.all().filter('api_key =', self.request.get('api_key')).get()
        
        channel = Channel.all().filter('target =', target).filter('source =', source).get()
        approval_notice = None
        if not channel and source and target:
            channel = Channel(target=target, source=source, outlet=target.get_default_outlet())
            channel.put()
            approval_notice = channel.get_approval_notice()
            channel.send_activation_email()
            
        if channel:
            notice = Notification(channel=channel, text=strip_tags(self.request.get('text')), icon=source.source_icon)
            for arg in ['title', 'link', 'icon', 'sticky', 'tags']:
                value = strip_tags(self.request.get(arg, None))
                if value:
                    setattr(notice, arg, value)
            notice.put()
            
            # Increment the counter on the channel to represent number of notices sent
            channel.count += 1
            channel.put()
            
            if channel.status == 'enabled':
                notice.dispatch()
                self.response.out.write("OK\n")
                
            elif channel.status == 'pending':
                self.response.set_status(202)
                if approval_notice:
                    approval_notice.dispatch()
                    self.response.out.write("OK\n")
                else:
                    self.response.out.write("202 Pending approval")
            elif channel.status == 'disabled':
                self.response.set_status(202)
                self.response.out.write("202 Accepted but disabled")
        else:
            self.error(404)
            self.response.out.write("404 Target or source not found")

class HistoryHandler(webapp.RequestHandler):
    def get(self):
        try:
            method, encoded = self.request.headers['AUTHORIZATION'].split()
            if method.lower() == 'basic':
                username, password = base64.b64decode(encoded).split(':')
                account = Account.all().filter('api_key =', username).get()
                if account:
                    notifications = Notification.get_history_by_target(account).fetch(20)
                    self.response.headers['Content-Type'] = 'application/json'
                    def to_json(notice):
                        o = notice.to_dict()
                        o['created'] = notice.created.strftime('%a %b %d %H:%M:%S +0000 %Y')
                        o['source_icon'] = notice.source.source_or_default_icon()
                        return simplejson.dumps(o)
                    self.response.out.write("[%s]" % ', '.join([to_json(n) for n in notifications]))
                else:
                    raise KeyError()
        except KeyError:
            self.response.headers['WWW-Authenticate'] = 'Basic realm="%s"' % 'Notify.io'
            self.error(401)

class ListenHandler(webapp.RequestHandler):
    def get(self, hash):
        if not 'Nio/1.0 CFNetwork' in self.request.headers['user-agent']:
            self.redirect('http://listen.notify.io/~1/listen/%s' % hash)
        else:
            message = memcache.get(self.request.remote_addr)
            if not message:
                memcache.set(self.request.remote_addr, True, time=300)
                self.response.out.write('{"text": "Click here to upgrade your client", "title": "This client is now deprecated", "link": "http://code.google.com/p/notify-io/downloads/detail?name=DesktopNotifier.dmg"}\n')
            else:
                time.sleep(20)

def main():
    application = webapp.WSGIApplication([
        ('/v1/notify/(.*)', NotifyHandler), 
        ('/v1/replay/(.*)', ReplayHandler), 
        ('/v1/listen/(.*)', ListenHandler),
        ('/api/history.json', HistoryHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
