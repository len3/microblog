from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm, oid
from forms import LoginForm, EditForm, PostForm
from models import User, ROLE_USER, ROLE_ADMIN, Post
from datetime import datetime


@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    user = g.user
    posts = g.user.followed_posts().all()
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, timestamp=datetime.utcnow(), author=g.user)
        db.session.add(post)
        db.session.commit()
        flash("Posted!")
        return redirect(url_for('index'))
    return render_template("index.html", title="home sweet home!",
                           user=user, form=form,
                           posts=posts)


@app.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for=['nickname', 'email'])

    return render_template('login.html', title="Sign In", form=form,
                           providers=app.config['OPENID_PROVIDERS'])

@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
    user_to_follow = User.query.filter_by(nickname=nickname).first()
    if user_to_follow == None:
        flash("Cannot follow the user %s because that user does not exist." % (nickname))
        return redirect(url_for('index'))

    if user_to_follow == g.user:
        flash("You can't follow yourself!")
        return redirect(url_for('user', nickname=nickname))

    if g.user.is_following(user_to_follow):
        flash("You are already following %s." % nickname)
        return redirect(url_for('user', nickname=nickname))

    #otherwise
    u = g.user.follow(user_to_follow)
    if u is None:
        flash("Cannot follow %s" % nickname)
        return redirect_for('user', nickname=nickname)
    db.session.add(u)
    db.session.commit()
    flash("You are now following %s" % (nickname))
    return redirect(url_for('user', nickname=nickname))


@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
    user_to_unfollow = User.query.filter_by(nickname=nickname).first()
    if user_to_unfollow == None:
        flash("Cannot unfollow the user %s because that user does not exist." % (nickname))
        return redirect(url_for('index'))
    if user_to_unfollow == g.user:
        flash("You can't unfollow yourself!")
        return redirect(url_for('user', nickname=nickname))
    if not g.user.is_following(user_to_unfollow):
        flash ("You are not following %s" % (nickname))
        return redirect(url_for('user', nickname=nickname))

    u = g.user.unfollow(user_to_unfollow)
    if u is None:
        flash("Cannot unfollow %s" % nickname)
        return redirect_for('user', nickname = nickname)
    db.session.add(u)
    db.session.commit()
    flash("You are no longer following %s" % (nickname))
    return redirect(url_for('user', nickname=nickname))


@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash("Invalid login. Please try again.")
        return redirect(url_for('login'))
    user = User.query.filter_by(email=resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        nickname = User.make_unique_nickname(nickname)
        user = User(nickname=nickname, email=resp.email, role=ROLE_USER)
        db.session.add(user)
        db.session.commit()
        db.session.add(user.follow(user))
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember=remember_me)
    return redirect(request.args.get('next') or url_for('index'))


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user is None:
        flash("User %s does not exist." % nickname)
        return redirect(url_for("index"))
    posts = [
        {'author': user, 'body': "this is a test post numero uno."},
        {'author': user,
         'body': "this is a test post numero dos equis."}
    ]
    print "about to render user.html"
    return render_template('user.html', user=user, posts=posts)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@login_required
@app.route('/edit', methods=["GET", "POST"])
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash("Your changes have been saved")
        return redirect(url_for('edit'))
    else:
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html', form=form)

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404
    
@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500
    