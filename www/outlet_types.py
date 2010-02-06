from django.utils import simplejson
from google.appengine.api import mail, xmpp, urlfetch
import urllib
from vendor import prowlpy 

class BaseOutlet(object):
    name = None
    push = True
    fields = []
    
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

	@classmethod
	def default_name(cls, params):
		return "Prowl for iPhone" 

	@classmethod
	def dispatch(cls, notice):
		api_key = notice.channel.outlet.get_param('api_key')
		p = prowlpy.Prowl(api_key)
		p.post(notice.source.source_name, notice.title or '', notice.text) 
		return None

class DesktopNotifier(BaseOutlet):
    name = "Desktop Notifier"
    push = False
    
    @classmethod
    def default_name(cls, params):
        return "A Desktop Notifier"
    
    @classmethod
    def dispatch(cls, notice):
        return ":".join([notice.channel.outlet.hash, notice.to_json()])



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

_globals = globals()
def get(outlet_name):
    return _globals[outlet_name]

available = ['DesktopNotifier', 'Email', 'Jabber', 'Webhook', 'Prowl']
all = [get(o) for o in available]