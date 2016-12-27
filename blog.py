#imports
import os
import re
from string import letters
import webapp2
import jinja2
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

#base class for handler. other handlers inherit from 
class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Hello blog!')

class TestHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Test passed')

app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/test', TestHandler)
], debug=True)
