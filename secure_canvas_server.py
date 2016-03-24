#!/usr/bin/env python3
import http.server
import ssl
import socketserver
import urllib.parse
import io

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
	pass

class CanvasHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
	protocol_version = 'HTTP/1.1'

	def do_GET(self):
		self.log_request()
		pr = urllib.parse.urlparse(self.path)
		pq = urllib.parse.parse_qs(pr.query)

		self.send_response(200)
		self.send_header('Content-Type','text/html')

		buf = io.BytesIO()
		request_uri = pq.get('redirect_uri', [''])[0]

		if len(request_uri):
			buf.write("<html><body><script>top.location.href = {};</script></body></html>".format(repr(request_uri)).encode())
		else:
			buf.write("<html><body><script>if(confirm('Move to the project page?'))top.location.href = {};</script></body></html>".format(repr('https://github.com/qbx2/DiffNotifier/')).encode())

		buf.seek(0)
		buf = buf.read()
		self.send_header('Content-Length',len(buf))
		self.end_headers()
		self.wfile.write(buf + b'\r\n')

	def do_POST(self):
		return self.do_GET()

BIND_ADDRESS = ('', 4443)
httpd = ThreadedHTTPServer(BIND_ADDRESS, CanvasHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(httpd.socket, certfile='./server.pem', server_side=True)

print('Server is running at {}'.format(':'.join(map(str,BIND_ADDRESS))))
httpd.serve_forever()
