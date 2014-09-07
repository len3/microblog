# models.py
from hashlib import md5
from app import db
ROLE_USER = 0
ROLE_ADMIN = 1


followers = db.Table('followers',
                     db.Column(
                         'follower_id', db.Integer, db.ForeignKey('user.id')),
                     db.Column(
                         'followed_id', db.Integer, db.ForeignKey('user.id'))
                     )


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True, unique=True)
    role = db.Column(db.SmallInteger, default=ROLE_USER)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(255))
    last_seen = db.Column(db.DateTime)
    followed = db.relationship('User', secondary=followers,
                               primaryjoin=(followers.c.follower_id == id),
                               secondaryjoin = (id == followers.c.followed_id),
                               backref = db.backref(
                                   'followers', lazy='dynamic'),
                               lazy = 'dynamic'
                               )

    def is_authenticated(self):
        return True

    def followed_posts(self):
        q =  Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(followers.c.follower_id == self.id).order_by(Post.timestamp.desc())
        #q = Post.all() # query.filter(Post.user_id == self.id)
#        import pdb; pdb.set_trace()
        return q

    def follow(self, follow_user):
        if not self.is_following(follow_user):
            self.followed.append(follow_user)
            return self

    def unfollow(self, follow_user):
        if self.is_following(follow_user):
            self.followed.remove(follow_user)
            return self

    def is_following(self, follow_user):
        #import pdb; pdb.set_trace()
        return self.followed.filter(followers.c.followed_id == follow_user.id).count() > 0

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def avatar(self, size):
        return 'http://www.gravatar.com/avatar/' + md5(self.email).hexdigest() + '?d=mm&s=' + str(size)

    @staticmethod
    def make_unique_nickname(nickname):
        # look up to see if the nickname exists
        uCheck = User.query.filter_by(nickname=nickname).first()
        if uCheck == None:
            return nickname
        suffix = 2
        while True:
            new_nickname = nickname + str(suffix)
            if User.query.filter_by(nickname=new_nickname).first() is None:
                break
            suffix += 1
        return new_nickname
        # if so, return a unique one
        # if not, return nickname

    def __repr__(self):
        return '<User %r>' % (self.nickname)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post %r>' % (self.body)
