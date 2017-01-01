#imports
import os
import re
import time
from string import letters
import webapp2
import jinja2
import random
import hmac
import hashlib
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = "thisIsASecret"
#functions for hashing and verifying hash
def make_hash(original):
    return hashlib.sha256(secret + original).hexdigest()

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val



def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)
#------------------------------------------------------------
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

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

#------------------------------------------------------------------------------
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

def posts_key(group = 'default'):
    return db.Key.from_path('posts', group)

def blog_key(name = 'default'):
    return db.Key.from_path('blogs', name)





#------------CLASSES FOR OBJECTS----------------------------------------------
class User(db.Model):
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


class Post(db.Model):
    creator_name = db.StringProperty(required=True)
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

    @classmethod
    def by_id(cls, post_id):
        return Post.get_by_id(post_id, parent = posts_key())

    def render(self, user=None, post_id=None):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self, user=user, post_id=post_id)

#------------HANDLERS---------------------------------------------------------
class TestHandler(BaseHandler):
    def get(self):
        self.response.write('Test passed')

class FrontPage(BaseHandler):
    
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc")
        if self.user:
            self.render("front-page.html", posts=posts, user = self.user)
        else:
            self.render("front-page.html", posts=posts)

class Login(BaseHandler):
    def get(self):
        self.render("login.html")
    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid login'

            self.render('login.html', error = msg, username=username)


class Signup(BaseHandler):
    def verify_pass(self, pw):
        if len(pw) >= 6:
            return True
        else:
            return False
    def user_exists(self, username):
        users = db.GqlQuery("select * from User")
        for user in users:
            if user.name == username:
                return True
        return False
        

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
            if self.user_exists(username):
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
                u = User.register(username, password)
                u.put()
                self.login(u)
                self.redirect('/')

        else:
            error = "No username or password provided"
            self.render_page(error=error)

class NewPost(BaseHandler):
    def get(self):
        if self.user:
            self.render("newpost.html", user=self.user)
        else:
            msg = "You need an account to post!"
            self.render("signup.html", error=msg)
            

    def post(self):

        subject = self.request.get("subject")
        content = self.request.get("content")
        creator = self.request.get("creator_name")
        p = Post(subject=subject, content=content, creator_name=creator)
        p.put()
        time.sleep(1)#allows time for database to store new information to be displayed on front page
        self.redirect("/")
        #self.write("content: " + p.content)
        #self.write("<br>subject: " + p.subject)
        #self.write(p.created)
        #self.write(p.last_modified)
        #self.write("<br>")
        #self.write(p.user_id)
        #p.put()

class Myposts(BaseHandler):
    def get(self):
        query = "select * from Post where creator_name='" + self.user.name + "'"
        print query
        myposts = db.GqlQuery(query)
        self.render("myposts.html", posts=myposts, user=self.user)

class Users(BaseHandler):
    def get(self):
        users = db.GqlQuery("select * from User")
        for user in users:
            self.write("name: " + user.name + " pass: " + user.pw_hash)
            self.write("<br>")

class Logout(BaseHandler):
    def get(self):
        self.logout()
        self.redirect('/')

class EditPost(BaseHandler):
    def get(self):
        post_id = self.request.get("post_id")
        posts = db.GqlQuery("select * from Post")
        subject = ""
        content = ""
        for post in posts:
            if post_id == str(post.key().id()):
                subject = post.subject
                content = post.content
                break
                
        self.render("newpost.html", content=content, subject=subject, user=self.user)

class DeletePost(BaseHandler):
    def get(self):
        post_id = self.requet.get("post_id")
        print post_id
#----------------------------------------------------------------------
app = webapp2.WSGIApplication([
    ('/', FrontPage),
    ('/test', TestHandler),
    ('/signup', Signup),
    ('/login', Login),
    ('/myposts', Myposts),
    ('/newpost', NewPost),
    ('/edit', EditPost),
    ('/delete', DeletePost),
    ('/logout', Logout),
    ('/users', Users)
], debug=True)
