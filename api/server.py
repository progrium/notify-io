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

NOTIFY_WWW = 'http://localhost:8091'

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

class RootResource(Resource):
    isLeaf = False
    
    @classmethod
    def setup(cls):
        r = cls()
        r.putChild('listen', ListenResource())
        r.putChild('notify', NotifyResource())
        return r
    

class NotifyResource(Resource):
    isLead = True
    
    def render_POST(self, request):
        hash = request.args.get('hash', [None])[0]
        if not hash:
            return "No hash"
        if not hash in listeners:
            listeners[hash] = []
        
        notification = {}
        for arg in ['title', 'text', 'icon', 'link', 'sticky']:
            value = request.args.get(arg, [None])[0]
            if value:
                notification[arg] = value
        for listener in listeners[hash]:
            listener.queue.put(simplejson.dumps(notification))
        client.getPage(url='%s/log?hash=%s' % (NOTIFY_WWW, hash), method='POST', postdata=urllib.urlencode(notification))
        return "ok"

class ListenResource(Resource):
    isLeaf = True
    
    def render_GET(self, request):
        hash = request.path.split('/')[-1]
        if not hash or hash == 'listen':
            return "No hash"
        if not hash in listeners:
            listeners[hash] = []
        request.queue = Queue(lambda m: self._send(request, m))
        listeners[hash].append(request)
        
        request.setHeader('Content-Type', 'application/json')
        request.setHeader('Transfer-Encoding', 'chunked')
        request.notifyFinish().addBoth(self._finished, hash, request)
        return server.NOT_DONE_YET
    
    def _finished(self, whatever, hash=None, request=None):
        listeners[hash].remove(request)

    def _send(self, request, message):
        request.write("%s\n" % message)

log.startLogging(sys.stdout)
reactor.listenTCP(8191, Site(RootResource.setup()))
reactor.run()