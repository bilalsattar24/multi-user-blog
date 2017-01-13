# Title: Multi-User-Blog
# Author: Bilal Sattar
# Description: This is the backend for the Udacity's
# Multi-user blog project.
# Date: 1/5/2017


# ----------------------------Imports---------------------------------------
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

# -----------------------------Variables--------------------------------------
secret = "thisIsASecret"
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


# -----------------------------Functions--------------------------------------


def make_hash(original):
    """
        salts password then returns hash of that combination
    """
    return hashlib.sha256(secret + original).hexdigest()


def make_secure_val(val):
    """
        returns the string that will be stored in a cookie
    """
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())


def check_secure_val(secure_val):
    """
        checks the secret against the hash
    """
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def render_str(template, **params):
    """
        renders html using template with passed in variables
    """
    t = jinja_env.get_template(template)
    return t.render(params)


def make_salt(length=5):
    """
        generates random 5 letter string to use as salt
    """
    return ''.join(random.choice(letters) for x in xrange(length))


def make_pw_hash(name, pw, salt=None):
    """
        combines sale and hash into comma separated string
    """
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)


def valid_pw(name, password, h):

    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

# These methods get keys for their corresponding objects


def users_key(group='default'):
    return db.Key.from_path('users', group)


def posts_key(group='default'):
    return db.Key.from_path('posts', group)


def blog_key(name='default'):
    return db.Key.from_path('blogs', name)


def comments_key(group='default'):
    return db.Key.from_path('comments', group)


# ----------------------Base Class----------------------------------
class BaseHandler(webapp2.RequestHandler):
    """
        This Base class has necessary methods for all other handlers and
        inherits the necessary webapp2.RequestHandler
        All other handlers will inherif from this class
    """
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        """
            renders html using template with passed in variables
        """
        return render_str(template, **params)

    def render(self, template, **kw):
        """
            helper function that calls render_str
        """
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        """
            sets cookie with secure values for login
        """
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val)
        )

    def read_secure_cookie(self, name):
        """
            verifies the cookie to check for login
        """
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        """
            logs in user by calling set cookie method
        """
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        """
            deletes cookie to log user out
        """
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        """
            checks if user is logged in
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

# -----------------------CLASSES FOR OBJECTS----------------------------------


class User(db.Model):
    """
        User class holds information about each user.
        This class will be used to store data into datastore
        Attributes:
            name (str): Username
            pw_hash (str): Hashed password of the post with salt.
            email (str): Email address
    """
    name = db.StringProperty(required=True)
    pw_hash = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent=users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw):
        pw_hash = make_pw_hash(name, pw)
        return User(parent=users_key(),
                    name=name,
                    pw_hash=pw_hash)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u


class Post(db.Expando):
    """
        Post class holds information about each post
        and helps to store/retrieve User data to/from database.
        Attributes:
            creator_name (str): Username of user that posted comment
            subject (str): Subject line of post
            content (text): Main text content of the post
            created (DateTime): Date/Time of post creation
            likers (strlist): List of user ID's who have liked the post
            numLikes(int): Number of likes for the posts_key
            comments(strlist): List of comments ID's on the post
            numComments(int): Number of comments on the post
    """
    creator_name = db.StringProperty(required=True)
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    likers = db.StringListProperty()
    numLikes = db.IntegerProperty()
    comments = db.StringListProperty()
    numComments = db.IntegerProperty(required=True)

    @classmethod
    def by_id(cls, post_id):
        """
            returns comment from id
        """
        return Post.get_by_id(post_id, parent=posts_key())

    def render(self, user=None, post_id=None, username="", *a, **kw):
        """
            replaces new lines with html <br> then renders page
        """
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p=self, user=user, post_id=post_id)


class Comment(db.Model):
    """
        Comment object stores all information about each comment
        and helps to store/retrieve User data to/from database.
        Attributes:
            post_id(str): ID of post that the comment is for
            content(text): The text of the comment
            created(DateTime): Time of original comment
            username(str): Username of commenter
    """
    post_id = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    username = db.StringProperty()

    @classmethod
    def by_id(cls, post_id):
        return cls.get_by_id(post_id, parent=posts_key())


# -------------------------------HANDLERS-------------------------------------
class TestHandler(BaseHandler):
    """
        This handler is for development and debugging purposes.
        It clears Users,Posts, and Comments in datastore
    """
    def get(self):
        comments = db.GqlQuery("select * from Comment")
        posts = db.GqlQuery("select * from Post")
        users = db.GqlQuery("select * from User")
        for user in users:
            user.delete()
        for post in posts:
            post.delete()
        for comment in comments:
            comment.delete()
        self.response.write('Test passed')


class FrontPage(BaseHandler):
    def get(self):
        posts = db.GqlQuery("select * from Post order by created desc")
        if self.user:
            self.render("front-page.html", posts=posts,
                        user=self.user, username=self.user.name)
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
            self.render('login.html', error=msg, username=username)


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
        self.render("signup.html", username=username,
                    password=password, error=error)

    def get(self):
        if self.user:
            return self.redirect("/myposts")
        self.render_page()

    def post(self):
        if self.user:
            return self.redirect("/myposts")
        username = self.request.get("username")

        # original password
        password = self.request.get("password")

        # re-entered password
        password2 = self.request.get("verify-password")

        # this block verifies all of the requirements for username and password
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

                # store new user in database
                # salt + hash before storing password
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
        if not self.user:
            return self.redirect('/login')

        subject = self.request.get("subject")
        content = self.request.get("content")
        creator = self.request.get("creator_name")
        p = Post(subject=subject, content=content,
                 creator_name=creator, numLikes=0, numComments=0)
        p.put()

        # allows time for database to store new information
        # to be displayed on front page
        time.sleep(1)
        self.redirect("/")


class Myposts(BaseHandler):
    def get(self):
        if self.user:
            query = "select * from Post where creator_name='" + \
                    self.user.name + "'order by created desc"
            myposts = db.GqlQuery(query)
            self.render("myposts.html", posts=myposts, user=self.user)
        else:
            msg = "Sign in to view your posts!"
            self.render("login.html", error=msg)


class Users(BaseHandler):
    """
        This handler is for development and debugging purposes
        Shows list of user with hashed password information
    """
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
                post_to_edit = post
                break
        if not self.user.name == post_to_edit.creator_name:
            return self.redirect('/')
        self.render("editpost.html", post_id=post_id, content=content,
                    subject=subject, user=self.user)

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")
        post_id = self.request.get("post_id")

        post_to_edit = None
        posts = db.GqlQuery("select * from Post")
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_edit = post
                break

        if not self.user.name == post_to_edit.creator_name:
            return self.redirect('/')

        post_to_edit.subject = subject
        post_to_edit.content = content
        post.put()
        time.sleep(1)
        self.redirect("/myposts")


class DeletePost(BaseHandler):
    def get(self):
        posts = db.GqlQuery("select * from Post")
        post_id = self.request.get("post_id")

        for post in posts:
            if post_id == str(post.key().id()):
                post_to_delete = post
                if self.user.name == post_to_delete.creator_name:
                    post.delete()
                    time.sleep(1)
                    return self.redirect("/myposts")

        msg = "Sign in to delete your posts!"
        self.render("login.html", error=msg)
        print post_id


class Like(BaseHandler):
    def get(self):
        if not self.user:
            self.redirect('/login')
            return
        post_id = self.request.get("post_id")
        posts = db.GqlQuery("select * from Post")
        post_to_like = None
        posted = False
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_like = post
                break
        if self.user:
            if post_to_like.creator_name == self.user.name:
                self.redirect('/')
                return
            user_id = str(self.user.key().id())
            print("user_id: " + user_id)
            likers = post_to_like.likers
            for liker in likers:

                # if post has already been liked by current user
                if user_id == liker:
                    posted = True
                    post_to_like.likers.remove(user_id)
                    post_to_like.numLikes -= 1
                    post_to_like.put()
                    self.redirect('/')
                    time.sleep(1)
                    break
        if not posted:
            post.likers.append((user_id))
            post_to_like.numLikes += 1
            post_to_like.put()
            time.sleep(1)
            self.redirect('/')


class Comments(BaseHandler):
    def get(self):
        post_id = str(self.request.get("post_id"))
        comments = db.GqlQuery("select * from Comment order by created desc")
        posts = db.GqlQuery("select * from Post")
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_pass = post
                break
        commentList = []
        for comment in comments:
            if comment.post_id == post_id:
                commentList.append(comment)
        self.render("comments.html", comments=commentList,
                    post=post, user=self.user)


class NewComment(BaseHandler):
    def get(self):
        if not self.user:
            self.redirect('/login')
            return
        comment = self.request.get("comment")
        post_id = self.request.get("post_id")
        posts = db.GqlQuery("select * from Post")
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_comment = post
                break

        comment = Comment(content=comment, post_id=post_id,
                          username=self.user.name)
        comment.put()
        post_to_comment.numComments += 1
        post_to_comment.put()
        time.sleep(1)
        self.redirect("/post?post_id={{p.key().id()}}")

    def post(self):
        comment = self.request.get("comment")
        post_id = self.request.get("post_id")
        posts = db.GqlQuery("select * from Post")
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_comment = post
                break

        comment = Comment(content=comment, post_id=post_id)
        comment.put()
        post_to_comment.numComments += 1
        post_to_comment.put()
        time.sleep(1)
        self.redirect("/post?post_id={{p.key().id()}}")


class PostPage(BaseHandler):
    def get(self):
        post_id = self.request.get("post_id")
        post_to_view = None

        posts = db.GqlQuery("select * from Post")
        comments = db.GqlQuery("select * from Comment order by created desc")
        self.write(comments)
        for post in posts:
            if post_id == str(post.key().id()):
                post_to_view = post
        self.render("permalink.html", user=self.user, post=post)


class DeleteComment(BaseHandler):
    def get(self):
        comment_id = self.request.get("comment_id")
        post_id = self.request.get("post_id")
        comment_to_delete = None
        post_to_alter = None
        comments = db.GqlQuery("select * from Comment")
        posts = db.GqlQuery("select * from Post")

        for post in posts:
            if post_id == str(post.key().id()):
                post_to_alter = post

        for comment in comments:
            if comment_id == str(comment.key().id()):
                comment_to_delete = comment

        if self.user.name == comment.username:
            print ("self.user.name: "+self.user.name)
            print ("comment.username: "+comment.username)
            post_to_alter.numComments -= 1
            post.put()
            comment_to_delete.delete()
            time.sleep(1)
            return self.redirect("/comments?post_id="+post_id)


class EditComment(BaseHandler):
    def get(self):
        comment_id = self.request.get("comment_id")
        post_id = post_id = self.request.get("post_id")
        comments = db.GqlQuery("select * from Comment")
        for comment in comments:
            if comment_id == str(comment.key().id()):
                comment_to_edit = comment
                break
        if not comment_to_edit.username == self.user.name:
            return self.redirect("/login")

        self.render("editcomment.html", user=self.user,
                    comment=comment_to_edit, post_id=post_id)

    def post(self):
        comment_id = self.request.get("comment_id")
        post_id = post_id = self.request.get("post_id")
        new_comment = self.request.get("new_comment")
        comments = db.GqlQuery("select * from Comment")
        for comment in comments:
            if comment_id == str(comment.key().id()):
                comment_to_edit = comment
                break
        if not comment_to_edit.username == self.user.name:
            return self.redirect("/login")

        comment_to_edit.content = new_comment
        comment_to_edit.put()
        time.sleep(1)
        return self.redirect("/comments?post_id="+post_id)

# -------------------------------Handler Mappings------------------------------
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
    ('/users', Users),
    ('/comments', Comments),
    ('/newcomment', NewComment),
    ('/like', Like),
    ('/deletecomment', DeleteComment),
    ('/editcomment', EditComment),
    ('/post', PostPage)
], debug=True)
