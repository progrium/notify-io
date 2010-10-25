from django.utils import simplejson
from google.appengine.api import mail, xmpp, urlfetch
import urllib
import logging

import keys
import base64
def push_to_realtime(hash, message):
    #urlfetch.make_fetch_call(urlfetch.create_rpc(),'https://AC43b69b055a6b5299cd211a53d82047bb.twiliort.com/~1/listen/%s' % hash, 
    urlfetch.fetch('https://AC43b69b055a6b5299cd211a53d82047bb.twiliort.com/~1/listen/%s' % hash, 
        method='POST', payload=message, headers={
            "Content-Type": "application/json", 
            "Authorization": 'Basic %s' % base64.encodestring('%s:x' % keys.auth_token)[:-1]})

class BaseOutlet(object):
    name = None
    push = True
    fields = []
    help = ""
    
    @classmethod
    def type(cls):
        return str(cls).split('.')[-1][:-2]
        
    @classmethod
    def default_name(cls, params):
        pass
    
    @classmethod
    def setup(cls, outlet):
        pass
    
    @classmethod
    def dispatch(cls, notice):
        return ":".join([notice.channel.outlet.hash, notice.to_json()])

class Prowl(BaseOutlet):
	name = "Prowl"
	fields = ['api_key']
	help = 'Get your API key at the <a href="http://prowl.weks.net/">Prowl website</a>.'
	
	@classmethod
	def default_name(cls, params):
		return "An iPhone with Prowl" 

	@classmethod
	def dispatch(cls, notice):
		api_key = notice.channel.outlet.get_param('api_key')
		data = {
		    'apikey': api_key,
            'application': notice.source.source_name,
            'event': notice.title or '',
            'description': notice.text,
	    }
		data = urllib.urlencode(utf8encode(data))
		urlfetch.fetch("https://prowl.weks.net/publicapi/add/", method='POST', payload=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
		return None
		
		

class DesktopNotifier(BaseOutlet):
    name = "Desktop Notifier"
    push = False
    
    @classmethod
    def default_name(cls, params):
        return "A Desktop Notifier"
    
    @classmethod
    def dispatch(cls, notice):
        push_to_realtime(notice.channel.outlet.hash, notice.to_json())



class Email(BaseOutlet):
    name = "Email"
    fields = ['email']
    
    @classmethod
    def default_name(cls, params):
        return "Email to %s" % params['email']
    
    @classmethod
    def dispatch(cls, notice):
        email = notice.channel.outlet.get_param('email')
        mail.send_mail(sender="%s <no-reply@notify-io.appspotmail.com>" % notice.source.source_name, to=email, \
            subject="[Notification] %s" % (notice.title or notice.text), \
            body="%s\n%s\n\n---\nSent by Notify.io" % (notice.text, (notice.link or '')))
        return None

class Jabber(BaseOutlet):
    name = "Jabber IM"
    fields = ['jid']
    
    @classmethod
    def default_name(cls, params):
        return "Send IM to %s" % params['jid']
    
    @classmethod
    def setup(cls, outlet):
        jid = outlet.get_param('jid')
        xmpp.send_invite(jid)
    
    @classmethod
    def dispatch(cls, notice):
        jid = notice.channel.outlet.get_param('jid')
        if xmpp.get_presence(jid):
            body = "%s: %s" % (notice.title, notice.text) if notice.title else notice.text 
            xmpp.send_message(jid, "%s %s [%s]" % (body, notice.link or '', notice.source.source_name))
        return None

class SMS(BaseOutlet):
    name = "SMS"
    fields = ['cellnumber', 'token']
    help = 'Get an access token at <a href="http://textauth.com/">TextAuth</a>.'
    
    @classmethod
    def default_name(cls, params):
        return "Send SMS to %s" % params['cellnumber']
    
    @classmethod
    def dispatch(cls, notice):
        cellnumber = notice.channel.outlet.get_param('cellnumber')
        token = notice.channel.outlet.get_param('token')
        if notice.title:
            body = "%s: %s [%s]" % (notice.title, notice.text, notice.source.source_name) 
        else:
            body = "%s [%s]" % (notice.text, notice.source.source_name)
        urlfetch.fetch('http://www.textauth.com/api/v1/send', method='POST', payload=urllib.urlencode({
            'to': cellnumber,
            'token': token,
            'body': body,
        }))
        return None

class Webhook(BaseOutlet):
    name = "Webhook"
    fields = ['url']
    
    @classmethod
    def default_name(cls, params):
        return "Webhook at %s" % params['url']
    
    @classmethod
    def dispatch(cls, notice):
        url = notice.channel.outlet.get_param('url')
        urlfetch.fetch(url, method='POST', payload=urllib.urlencode(notice.to_dict()))
        return None

def utf8encode(source):
    return dict([(k, v.encode('utf-8') if v else None) for (k, v) in source.items()])

_globals = globals()
def get(outlet_name):
    return _globals[outlet_name]

available = ['DesktopNotifier', 'Email', 'Jabber', 'SMS', 'Webhook', 'Prowl']
all = [get(o) for o in available]
