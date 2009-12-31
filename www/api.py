import wsgiref.handlers
import hashlib, time, os

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from django.utils import simplejson

from models import Account, Notification, Channel
from app import API_HOST, API_VERSION, RequestHandler

class ListenAuthHandler(RequestHandler):
    def get(self):
        api_key = self.request.get('api_key')
        userhash = self.request.get('hash')
        account = Account.all().filter('hash =', userhash).filter('api_key =', api_key).get()
        if account:
            self.response.out.write("ok")
        else:
            self.error(403)

class NotificationHandler(RequestHandler):
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

def main():
    application = webapp.WSGIApplication([
        ('/notification', NotificationHandler), 
        ('/auth', ListenAuthHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
