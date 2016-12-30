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

#------------CLASSES FOR OBJECTS----------------------------------------------
class User(db.Model):
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()



class Post(db.Model):
    user_id = db.IntegerProperty(required=True)
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

#------------HANDLERS---------------------------------------------------------
class TestHandler(BaseHandler):
    def get(self):
        self.response.write('Test passed')

class FrontPage(BaseHandler):
    def get(self):
        self.render("front-page.html")

class Login(BaseHandler):
    def get(self):
        self.render("login.html")


class Signup(BaseHandler):
    def verify_pass(self, pw):
        if len(pw) >= 8:
            return True
        else:
            return False
    def verify_user(self, user):
        #return true if username does not already exist in the database
        return True
        #return false if username DOES exist

    def render_page(self, username="", password="", error=""):
        self.render("signup.html", username=username, password=password, error=error)

    def get(self):
        self.render_page()

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")#original password
        password2 = self.request.get("verify-password")#re-entered password
        
        #this block verifies all of the requirements for username and password
        if username and not password:
            error = "No password provided"
            self.render_page(error=error, username=username)
        elif not username and password:
            error = "No username provided"
            self.render_page(error=error)
        elif username and password and password2:
            if not self.verify_user(username):
                error = "Username already exsists"
                self.render_page(error=error)
            elif not self.verify_pass(password):
                error = "Password must be 8 characters or longer"
                self.render_page(error=error)
            elif password != password2:
                error = "Passwords don't match, try again"
                self.render_page(error=error)
            else:
                #store new user in database
                self.write("SUCCESS!")
        else:
            error = "No username or password provided"
            self.render_page(error=error)
        #----------------------------------------------------------------------

app = webapp2.WSGIApplication([
    ('/', FrontPage),
    ('/test', TestHandler),
    ('/signup', Signup),
    ('/login', Login),
    ('/newpost', NewPost)
], debug=True)
