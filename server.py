from http.server import HTTPServer
from http.server  import BaseHTTPRequestHandler
import cgi,json,os
from urllib.parse import urlparse
from urllib.parse import parse_qs
import grequests
import urllib
import tweepy

from keys import *

# consumer_key = CONSUMER_KEY
# consumer_secret = CONSUMER_SECRET
# access_token = ACCESS_TOKEN
# access_token_secret = ACCESS_TOKEN_SECRET

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth,timeout=1)

PORT = os.environ['PORT']
# PORT = 8000
TIMEOUT = 1

class RestHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=UTF-8')
        self.end_headers()

        url = self.path
        print(url)
        if  "/?q=" not in url:
            return
        o = urlparse(url)
        query = parse_qs(o.query)
        q = query.get('q')
        if(not q):
            q = [ "", ]

        a = urllib.parse.urlencode([("q", q[0]),("format","json")])
        urls = [
        	"http://api.duckduckgo.com/?" + a,
            "https://www.googleapis.com/customsearch/v1?key=" + GOOGLEKEY1 + "&cx=" + SEARCHENGINEKEY1 + "&" + a,
        ]

        t=0
        try:
            tweet = api.search(q[0])
        except Exception as e:
            t = 1

        reqs = (grequests.get(url, timeout=TIMEOUT) for url in urls)
        def exp(request, exception):
        	print(exception)
        res = grequests.map(reqs, exception_handler=exp)

        results = {}

        # Duck Duck Go
        if res[0] is not None:
            if res[0].status_code == 200:
                j = json.loads(res[0].text)
                if len(j['Results']) > 0:
                    results['duckduckgo'] = { 'url': j['Results'][0]['FirstURL'], 'text': j['Results'][0]['Text'] }
                elif len(j['RelatedTopics']) > 0:
                    results['duckduckgo'] = { 'url': j['RelatedTopics'][0]['FirstURL'], 'text': j['RelatedTopics'][0]['Text'] }
                else:
                    results['duckduckgo'] = { 'error': 'No result was found' }
            else:
                results['duckduckgo'] = { 'error': 'Server responded with status code' + str(res[0].status_code) + res[0].reason }
        else:
            results['duckduckgo'] = { 'error': 'API timed out' }

        # Google
        if res[1] is not None:
            if res[1].status_code == 200:
                k = json.loads(res[1].text)
                print(k)
                if 'items' in k:
                    results['google'] = { 'url': k['items'][0]['link'], 'text' : k['items'][0]['snippet'] }
                else:
                    results['google'] = { 'error': "google not returning items on server"}
            elif res[1].status_code == 403:
                k = json.loads(res[1].text)
                results['google'] = { 'error':  k["error"]["errors"][0]["reason"]}
            else:
                results['google'] = { 'error': 'Server responded with status code ' + str(res[1].status_code) + " " + res[1].reason }
        else:
            results['google'] = { 'error': 'API timed out' }

        # Twitter
        if t==0:
            results['twitter'] = { 'url': str('http://twitter.com/') + str(tweet[0].author.screen_name) ,'text':str(tweet[0].text) }
        else:
            results['twitter'] = { 'error' : "Twitter Timed out!"}

        temp = {"query": q[0], "results": results}
        self.wfile.write(bytes(json.dumps(temp, sort_keys=True, indent=4),"utf-8"))
        return


if __name__ == "__main__":
    try:
        server = HTTPServer(('', int(PORT)), RestHTTPRequestHandler)
        print('Started http server')
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, shutting down server')
        server.socket.close()
