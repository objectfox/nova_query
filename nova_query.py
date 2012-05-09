#!/usr/bin/env python

# Copyright (c) 2012 Jeff Kramer

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import argparse
import os
import urllib2
import xml.dom.minidom
import sys

def get_keystone_token(**args):
	'''
	Gets a keystone token from a keystone identity service.
	
	username = keystone username
	password = keystone password
	
	or
	
	accesskey = keystone access key
	secretkey = keystone secret key
	
	tenant_id = keystone tenant id
	identity_url = keystone url
	
	'''
	if 'accesskey' in args:
		identity_request = {
			'auth' : {
				'apiAccessKeyCredentials' : {
					'accessKey' : args['accesskey'],
					'secretKey' : args['secretkey']
				},
				"tenantId": args['tenant_id']
			}
		}
	elif 'username' in args:
		identity_request = {
			'auth' : {
				'passwordCredentials' : {
					'username' : args['username'],
					'password' : args['password']
				},
				"tenantId": args['tenant_id']
			}
		}
	else:
		raise StandardError('Need username or accesskey to request token.')
	identity_url = args['identity_url']
	
	if identity_url[-1] != '/':
		identity_url += '/'
	
	identity_request_json = json.dumps(identity_request)
	
	request = urllib2.Request(identity_url+'tokens',
		identity_request_json, {'Content-type':'application/json'})
	try:
		response = urllib2.urlopen(request).read()
	except urllib2.HTTPError, e:
		raise StandardError("HTTP Error from identity service: "+str(e))
		
	response_json = json.loads(response)
	
	return response_json['access']['token']['id']
	
def get_nova_token(**args):
	'''
	Gets a token from a nova service.
	
	username = nova username
	api_key = nova api key
	url = nova url
	
	
	'''
	
	request = urllib2.Request(args['url'],None, {'X-Auth-Key':args['api_key'],'X-Auth-User':args['username']})
	response = urllib2.urlopen(request)
	info = dict(response.info())
	return info['x-server-management-url'],info['x-auth-token']


def nova_query(**args):
	'''
	Make a query to the Nova API Service
	
	nova auth:
	token = nova api token
	project_id = nova project ID
	url = nova API url
	
	keystone auth:
	token = keystone token
	url = nova API url
	tenant_id = nova Tenant (postpends to Nova API url)
	
	path = path to request
	data = post data
	'''

	if 'project_id' in args:
		url = args['url']
	else:
		if args['tenant_id'] == args['url'][-int(len(args['tenant_id'])):]:
			url = args['url']
		elif args['nova_url'][-1:] == '/':
			url = args['url']+args['tenant_id']
		else:
			url = args['url']+"/"+args['tenant_id']
	if args['data']:
		if args['data'][0] == '<':
			contenttype = "application/xml"
		elif args['data'][0] == '{':
			contenttype = "application/json"
		else:
			contenttype = "application/x-html-encoded"

	if 'project_id' in args:
		if args['data']:
			request = urllib2.Request(url+args['path'], args['data'], {'X-Auth-Token':args['token'],'X-Auth-Project-Id':args['project_id'],"Content-type":contenttype})
		else:
			request = urllib2.Request(url+args['path'], None, {'X-Auth-Token':args['token'],'X-Auth-Project-Id':args['project_id']})
	else:
		if args['data']:
			request = urllib2.Request(url+args['path'],
			args['data'], {'X-Auth-Token':args['token'],"Content-type":contenttype})
		else:
			request = urllib2.Request(url+args['path'],
			None, {'X-Auth-Token':args['token']})
	
	if args['method']:
		request.get_method = lambda: args['method']
	
	try:
		response = urllib2.urlopen(request)
	except urllib2.HTTPError, e:
		raise StandardError("HTTP Error from compute service: "+str(e))
	
	return response.read()
			


if __name__ == '__main__':
	
	# Parse our arguments.
	
	parser = argparse.ArgumentParser(
		formatter_class=argparse.RawDescriptionHelpFormatter,
		description='''
Make requests to Nova API endpoints.

examples:
	Get a list of servers:
	nova_query.py /servers.json
	
	Show a specific server's details:
	nova_query.py /servers/1234.xml
	
	Show only images named uec-natty pretty-printed:
	nova_query.py -p /images.json?name=uec-natty
	
	Delete a keypair named 'mykeypair':
	nova_query.py -m DELETE /os-keypairs/mykeypair

	Create a new server named 'Server 1':
	nova_query.pl -d "{\\"server\\": {\\"name\\": \\"Server 1\\", \\ 
	\\"imageRef\\": 1, \\"flavorRef\\": 1}}" /servers.xml

	Pipe post data in on stdin:
	cat mykeypair.json | nova_query.py -i /os-keypairs
	
''',
		epilog='''
note:
  For v1.1 Nova Auth clusters NOVA_API_KEY, NOVA_USERNAME, NOVA_PROJECT_ID
  and NOVA_URL environment variables must be set

  For v2.0 Keystone Auth clusters NOVA_USERNAME and NOVA_PASSWORD or
  NOVA_ACCESSKEY and NOVA_SECRETKEY must be set, as well as NOVA_TENANT_ID,
  NOVA_IDENTITY_URL and NOVA_URL.
	'''	)
	parser.add_argument('arguments', metavar='path', type=str, nargs=1,
		help="url path to request")
	parser.add_argument('-p',dest='request_pretty', action='store_true',
		help='make the request and pretty print response')
	parser.add_argument('-i',dest='read_stdin', action='store_true',
		help='read data from stdin')
	parser.add_argument('-m',dest='method', type=str,
		help='HTTP method to use (DELETE for removal)')
	parser.add_argument('-d',dest='post_data', type=str, help="data to post")
	args = parser.parse_args()
	
	# Ensure our environment variables are set.
	
	auth_method = {
		"NOVA_API_KEY" :  ("NOVA_API_KEY","NOVA_USERNAME","NOVA_PROJECT_ID",
		"NOVA_URL"),
		"NOVA_USERNAME" : ("NOVA_USERNAME","NOVA_PASSWORD","NOVA_TENANT_ID",
		"NOVA_IDENTITY_URL","NOVA_URL"),
		"NOVA_ACCESSKEY" : ("NOVA_ACCESSKEY","NOVA_SECRETKEY","NOVA_TENANT_ID",
		"NOVA_IDENTITY_URL","NOVA_URL")
		}
	
	if (args.read_stdin):
		data = sys.stdin.read()
	elif (args.post_data):
		data = args.post_data
	else:
		data = None
	
	chosen_method = ''
	for method in auth_method:
		if (len(list(set(auth_method[method]).intersection(os.environ))) == len(auth_method[method])):
			chosen_method = method

	if chosen_method in ('NOVA_USERNAME','NOVA_ACCESSKEY'):
		token = get_keystone_token(username=os.getenv('NOVA_USERNAME'),
			password=os.getenv('NOVA_PASSWORD'),
			accesskey=os.getenv('NOVA_ACCESSKEY'),
			secretkey=os.getenv('NOVA_SECRETKEY'),
			tenant_id=os.getenv('NOVA_TENANT_ID'),
			identity_url=os.getenv('NOVA_IDENTITY_URL'))
		response = nova_query(url=os.getenv('NOVA_URL'),
			path=args.arguments[0],tenant_id=os.getenv('NOVA_TENANT_ID'),
			data=data,token=token,method=args.method)
	elif chosen_method in ('NOVA_API_KEY'):
		(url,token) = get_nova_token(username=os.getenv('NOVA_USERNAME'),
			api_key=os.getenv('NOVA_API_KEY'),
			url=os.getenv('NOVA_URL'))
		response = nova_query(url=url,project_id=os.getenv('NOVA_PROJECT_ID'),
			path=args.arguments[0],data=data,token=token,method=args.method)
	else:
		raise StandardError, "Environment variables must be set."
	
	if args.request_pretty:
		if response[0] == '<':
			print xml.dom.minidom.parseString(response).toprettyxml()
		elif response[0] == '{':
			print json.dumps(json.loads(response), indent=4)
		else:
			print response
	else:
		print response

	
	
	
	
	
