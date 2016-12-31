#imports
import os
import re
import time
from string import letters
import webapp2
import jinja2
import hashlib
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = "thisIsASecret"
#functions for hashing and verifying hash
def make_hash(original):
    return hashlib.sha256(secret + original).hexdigest()

def make_secure_val(str):
    return "%s,%s" % (str, make_hash(original))

def check_secure_val(secure_val):
    val = h.split('|')[0]
    if secure_val == make_secure_val(val):
        return val



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

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val)
        )
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    #def initialize(self, *a, **kw):
        #webapp2.RequestHandler.initialize(self, *a, **kw)
        #uid = self.read_secure_cookie('user-id')
        #self.user = uid and User.by_id(int(uid))

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

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)

#------------HANDLERS---------------------------------------------------------
class TestHandler(BaseHandler):
    def get(self):
        self.response.write('Test passed')

class FrontPage(BaseHandler):
    
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc")
        self.render("front-page.html", posts=posts)

class Login(BaseHandler):
    def get(self):
        self.render("login.html")


class Signup(BaseHandler):
    def verify_pass(self, pw):
        if len(pw) >= 6:
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
                error = "Password must be 6 characters or longer"
                self.render_page(error=error)
            elif password != password2:
                error = "Passwords don't match, try again"
                self.render_page(error=error, username=username)
            else:
                #store new user in database
                #salt + hash before storing password
                self.write("SUCCESS!")
        else:
            error = "No username or password provided"
            self.render_page(error=error)
        #----------------------------------------------------------------------

class NewPost(BaseHandler):
    def get(self):
        self.render("newpost.html")

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")
        p = Post(user_id=1,subject=subject, content=content)
        p.put()
        time.sleep(2)#allows time for database to store new information to be displayed on front page
        self.redirect("/")
        #self.write("content: " + p.content)
        #self.write("<br>subject: " + p.subject)
        #self.write(p.created)
        #self.write(p.last_modified)
        #self.write("<br>")
        #self.write(p.user_id)
        #p.put()
app = webapp2.WSGIApplication([
    ('/', FrontPage),
    ('/test', TestHandler),
    ('/signup', Signup),
    ('/login', Login),
    ('/newpost', NewPost)
], debug=True)
