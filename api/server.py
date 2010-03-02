from twisted.web import client, error, http, server
from twisted.web.resource import Resource
from twisted.python import log
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.internet.defer import DeferredQueue
import sys, simplejson, urllib

try:
    if sys.argv[1] == '--dev':
        # Development
        NOTIFY_WWW = 'http://localhost:8081'
        PORT = 9090
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


class ReplayResource(Resource):
    isLeaf = True

    def render_GET(self, request):
        return "Method not allowed"
    
    def render_POST(self, request):
        api_key = request.args.get('api_key', [request.getUser()])[0]
        if not api_key:
            request.setHeader('WWW-Authenticate', 'Basic realm="%s"' % 'Notify.io')
            errpage = error.ErrorPage(http.UNAUTHORIZED, "Unauthorized", "401 Authentication (API key) required")
            return errpage.render(request)
        
        hash = request.path.split('/')[-1].lower()
        if not hash or hash == 'notify':
            return "No hash"
        
        client.getPage(url='%s/api/replay/%s' % (NOTIFY_WWW, hash), method='POST', postdata=urllib.urlencode({'api_key': api_key})) \
                .addCallback(self.replay_success, request) \
                .addErrback(self.replay_failure, request)
                
        return server.NOT_DONE_YET

    def replay_success(self, page_contents, request):
        if page_contents[0:3] != '202':
            if ':' in page_contents:
                hashes, message = page_contents.split(':', 1)
                for hash in hashes.split(','):
                    for listener in listeners[hash]:
                        listener.queue.put(message.strip())
            request.write("OK\n")
        else:
            request.write(page_contents)
        request.finish()
    
    def replay_failure(self, failure, request):
        request.write(str(failure))
        request.finish()

class NotifyResource(Resource):
    isLeaf = True

    def render_GET(self, request):
        return "Method not allowed"
    
    def render_POST(self, request):
        api_key = request.args.get('api_key', [request.getUser()])[0]
        if not api_key:
            request.setHeader('WWW-Authenticate', 'Basic realm="%s"' % 'Notify.io')
            errpage = error.ErrorPage(http.UNAUTHORIZED, "Unauthorized", "401 Authentication (API key) required")
            return errpage.render(request)
        
        hash = request.path.split('/')[-1].lower()
        if not hash or hash == 'notify':
            return "No hash"
        
        if not hash in listeners:
            listeners[hash] = []
        
        notification = {}
        for arg in ['title', 'text', 'icon', 'link', 'sticky', 'tags']:
            value = request.args.get(arg, [None])[0]
            if value:
                notification[arg] = value
        notification['api_key'] = api_key
        
        client.getPage(url='%s/api/notify/%s' % (NOTIFY_WWW, hash), method='POST', postdata=urllib.urlencode(notification)) \
            .addCallback(self.notify_success, hash, request) \
            .addErrback(self.notify_failure, request)
                
        return server.NOT_DONE_YET

    def notify_success(self, page_contents, hash, request):
        if page_contents[0:3] != '202':
            if ':' in page_contents:
                hashes, message = page_contents.split(':', 1)
                for hash in hashes.split(','):
                    for listener in listeners[hash]:
                        listener.queue.put(message.strip())
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
        
        if not hash in listeners:
            listeners[hash] = []
        request.queue = Queue(lambda m: self._send(request, m))
        listeners[hash].append(request)
        
        request.setHeader('Content-Type', 'application/json')
        request.notifyFinish().addBoth(self._finished, hash, request)
        
        return server.NOT_DONE_YET
        
    def _finished(self, whatever, hash=None, request=None):
        listeners[hash].remove(request)

    def _send(self, request, message):
        request.write("%s\n" % message)

log.startLogging(sys.stdout)
reactor.listenTCP(PORT, Site(ContainerResource(
    v1=ContainerResource(
        listen=ListenResource(),
        notify=NotifyResource(),
        replay=ReplayResource(),
    )
)))
reactor.run()