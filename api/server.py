from twisted.web import client, error, http, server
from twisted.web.resource import Resource
from twisted.python import log
from twisted.internet import reactor
from twisted.web.server import Site
import sys
from twisted.internet.defer import DeferredQueue
import simplejson
from twisted.web import client
import urllib

try:
    if sys.argv[1] == '--dev':
        # Development
        NOTIFY_WWW = 'http://localhost:8091'
        PORT = 8191
except IndexError:
    # Production
    NOTIFY_WWW = 'http://www.notify.io'
    PORT = 8003

listeners = {} # Key: hash, Value: list of requests listening

class Queue(DeferredQueue):
    def __init__(self, handler=None):
        DeferredQueue.__init__(self)
        self.message_handler = handler
        def f(msg):
            if self.message_handler:
                self.message_handler(msg)
            else:
                self.receivedMessage(msg)
            self.get().addCallback(f)
        self.get().addCallback(f)

class ContainerResource(Resource):
    isLeaf = False
    def __init__(self, **kwargs):
        Resource.__init__(self)
        for key in kwargs:
            self.putChild(key, kwargs[key])


class NotifyResource(Resource):
    isLeaf = True

    def render_GET(self, request):
        return "Method not allowed"
    
    def render_POST(self, request):
        hash = request.path.split('/')[-1].lower()
        if not hash or hash == 'notify':
            return "No hash"
        api_key = request.args.get('api_key', [request.getUser()])[0]
        if not api_key:
            return "No api key"
            
        if not hash in listeners:
            listeners[hash] = []
        
        replay = request.args.get('replay', [None])[0]
        if replay:
            client.getPage(url='%s/notification?hash=%s&api_key=%s&replay=%s' % (NOTIFY_WWW, hash, api_key, replay), method='POST') \
                .addCallback(self.notify_success, hash, request) \
                .addErrback(self.notify_failure, request)
                
        else:
            notification = {}
            for arg in ['title', 'text', 'icon', 'link', 'sticky']:
                value = request.args.get(arg, [None])[0]
                if value:
                    notification[arg] = value
            
            client.getPage(url='%s/notification?hash=%s&api_key=%s' % (NOTIFY_WWW, hash, api_key), method='POST', postdata=urllib.urlencode(notification)) \
                .addCallback(self.notify_success, hash, request) \
                .addErrback(self.notify_failure, request)
                
        return server.NOT_DONE_YET

    def notify_success(self, page_contents, hash, request):
        if page_contents[0:3] != '202':
            for listener in listeners[hash]:
                listener.queue.put(page_contents)
            request.write("OK\n")
        else:
            request.write(page_contents)
        request.finish()
    
    def notify_failure(self, failure, request):
        request.write(str(failure))
        request.finish()

class ListenResource(Resource):
    isLeaf = True
    
    def render_GET(self, request):
        hash = request.path.split('/')[-1].lower()
        if not hash or hash == 'listen':
            return "No hash"
        api_key = request.args.get('api_key', [request.getUser()])[0]
        if not api_key:
            return "No api key"
            
        client.getPage(url='%s/auth?hash=%s&api_key=%s' % (NOTIFY_WWW, hash, api_key)) \
            .addCallback(self.start_stream, hash, request) \
            .addErrback(self.write_error, request)
        
        return server.NOT_DONE_YET
        
    def start_stream(self, whatever, hash=None, request=None):    
        if not hash in listeners:
            listeners[hash] = []
        request.queue = Queue(lambda m: self._send(request, m))
        listeners[hash].append(request)
        
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Transfer-Encoding', 'chunked')
        request.notifyFinish().addBoth(self._finished, hash, request)
    
    def write_error(self, failure, request):
        request.write(str(failure))
        request.finish()

    
    def _finished(self, whatever, hash=None, request=None):
        listeners[hash].remove(request)

    def _send(self, request, message):
        request.write("%s\n" % message)

log.startLogging(sys.stdout)
reactor.listenTCP(PORT, Site(ContainerResource(
    v1=ContainerResource(
        listen=ListenResource(),
        notify=NotifyResource()
    )
)))
reactor.run()