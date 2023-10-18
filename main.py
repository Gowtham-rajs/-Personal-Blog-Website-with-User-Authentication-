from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import sqlite3, os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ["Key_Flask"]
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)






# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)



class new(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password
        self.authenticated = False

    def is_active(self):
        return self.is_active()

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return self.authenticated

    def is_active(self):
        return True

    def get_id(self):
        return self.id


@login_manager.user_loader
def load_user(user_id):
    lu= cur.execute("SELECT * from user where id = '{id}'".format(id = user_id)).fetchone()


    if lu is None:
        return None

    else:
        return new(int(lu[0]),lu[1],lu[2])

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


# TODO: Create a User table for all your registered users. 
con = sqlite3.connect("instance/blog.db",check_same_thread=False)
cur = con.cursor()



def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

with app.app_context():
    db.create_all()

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


@app.route('/register', methods= ["GET","POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        password_hash = generate_password_hash(password= request.form["password"], method='pbkdf2', salt_length=5)

        cur.execute("""insert into user (email, password, name) values ('{email}', '{passk}','{name}')
        """.format(email = request.form["email"], passk =password_hash ,name = request.form["name"]) )
        con.commit()
        return redirect(url_for("login"))
    return render_template("register.html", form =form)


@app.route('/login', methods= ["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        user_email =con.execute("select * from user where email = '{email}'".format(email=request.form["email"])).fetchone()
        try:
            if check_password_hash(pwhash = user_email[2]  ,password= request.form["password"]):
                load = load_user(user_email[0])
                login_user(load)
                load.authenticated = True
                global current_user
                current_user = load
                print(type (current_user),current_user.id)
                return redirect(url_for("get_all_posts", access = load.authenticated))

        except TypeError:
            flash("Incorrect Email address")
            return render_template("login.html", form= form)
        else:
            flash("Incorrect Password")
            return render_template("login.html", form=form)

    return render_template("login.html", form= form)


@app.route('/logout')
def logout():
    logout_user()
    global current_user
    current_user = None

    return redirect(url_for('get_all_posts'))



@app.route('/', methods= ["GET"])
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    print(request.args.get("access"))
    if request.args.get("access"):
        return render_template("index.html", all_posts=posts, access = current_user.authenticated, user  = current_user.id )
    return render_template("index.html", all_posts=posts, gravatar= gravatar)

@app.route("/post/<int:post_id>", methods= ["GET", "POST"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    print(post_id)
    ck = CommentForm()
    if request.method == "POST":
        try :
            if current_user.authenticated:
                cmt = request.form.to_dict()["commend"]
                cur.execute("""insert into mt (post_id, text) values ('{post_id}', '{text}')
                """.format(post_id=post_id, text=cmt))
                con.commit()

                return render_template("post.html", post=requested_post, access=current_user.authenticated,
                                   user=current_user.id, form=ck,
                                   cmt = cmt)
        except AttributeError :
            flash("Login first ")
            return redirect(url_for("login"))
    return render_template("post.html", post=requested_post, user  = current_user, form =ck, access=current_user.authenticated )


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@admin_only
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        post.author = "Gowtham"
        post.date = date.today().strftime("%B %d, %Y")
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5002)
