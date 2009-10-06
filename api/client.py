from twisted.web.http import HTTPClient
from twisted.web.client import HTTPClientFactory
from twisted.web import server, resource, error, http
from twisted.internet import reactor
from twisted.python import log
import simplejson as json
from twisted.web import client
from Growl import GrowlNotifier, Image
import sys

notifier = GrowlNotifier('notify.io', notifications=['notify'])
notifier.register()

def sendGrowl(notice):
    def notify(notice, icon=None):
        notifier.notify('notify', 
            notice.get('title', ''), 
            notice['text'], 
            sticky=notice.get('sticky', False), 
            icon=icon)
    if 'icon' in notice:
        client.getPage(notice['icon']) \
            .addCallback(lambda x: notify(notice, Image.imageWithData(x))) \
            .addErrback(lambda x: notify(notice))
    else:
        notify(notice)
    
            
class CometStream(HTTPClient):
    stream = 0
    
    def sendCommand(self, command, path):
        self.transport.write('%s %s HTTP/1.1\r\n' % (command, path))
    
    def lineReceived(self, line):
        if not self.stream:
            if line == "":
                self.stream = 1
        else:
            try:
                if '{' in line:
                    notice = json.loads(line)
                    sendGrowl(notice)
                    print notice
            except ValueError, e:
                pass
        
    def connectionMade(self):
        self.sendCommand('GET', self.factory.path)
        self.endHeaders()
        print "Connected and receiving..."

class CometFactory(HTTPClientFactory):
    protocol = CometStream

log.startLogging(sys.stdout)
f = CometFactory('http://localhost:8191/listen/55502f40dc8b7c769880b10874abc9d0')
reactor.connectTCP('localhost', 8191, f)
reactor.run()