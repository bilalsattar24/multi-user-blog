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

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
#base class for handler. other handlers inherit from 
class BaseHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    def render_str(self, template, **params):
        return render_str(template, **params)
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

class TestHandler(BaseHandler):
    def get(self):
        self.response.write('Test passed')

class FrontPage(BaseHandler):
    def get(self):
        self.render("front-page.html")


class Signup(BaseHandler):
    def get(self):
        self.render("signup.html")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        if username and password:
            self.write("username: " + username)
            self.write(" password: " + password)
        else:
            error = "no username and/or password"
            self.render("signup.html", error = error)


app = webapp2.WSGIApplication([
    ('/', FrontPage),
    ('/test', TestHandler),
    ('/signup', Signup)
], debug=True)
