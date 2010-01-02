from django.utils import simplejson

class BaseOutlet(object):
    name = None
    push = True
    fields = []
    
    def __init__(self, outlet_data):
        self.data = outlet_data
        self.params = simplejson.loads(outlet_data.params)
    
    @classmethod
    def type(cls):
        return str(cls).split('.')[-1][:-2]
        
    @classmethod
    def default_name(cls, params):
        pass

class DesktopNotifier(BaseOutlet):
    name = "Desktop Notifier"
    push = False
    
    @classmethod
    def default_name(cls, params):
        return "A Desktop Notifier"

class Email(BaseOutlet):
    name = "Email"
    fields = ['email']
    
    @classmethod
    def default_name(cls, params):
        return "Email to %s" % params['email']

class Jabber(BaseOutlet):
    name = "Jabber IM"
    fields = ['jid']
    
    @classmethod
    def default_name(cls, params):
        return "Send IM to %s" % params['jid']

class Webhook(BaseOutlet):
    name = "Webhook"
    fields = ['url']
    
    @classmethod
    def default_name(cls, params):
        return "Webhook at %s" % params['url']

_globals = globals()
def get(outlet_name):
    return _globals[outlet_name]

available = ['DesktopNotifier', 'Email', 'Jabber', 'Webhook']
all = [get(o) for o in available]