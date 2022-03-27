from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint("blog", __name__)


@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    db = get_db()

    posts = db.execute(
        # "SELECT p.id, title, body, created, author_id, username"
        # " FROM post p"
        # " JOIN user u ON p.author_id = u.id"
        # " ORDER BY created DESC"

        "SELECT *, l.author_id as love_author, count(distinct l.id)  as likes"
        " FROM post p"
        " LEFT JOIN user u ON p.author_id = u.id"
        " LEFT JOIN love l ON p.id = l.post_id"
        " GROUP BY p.id"
        " ORDER BY created DESC"

        # "SELECT p.id, title, body, created, author_id, username, count(distinct love.id)"
        # " FROM post p"
        # " LEFT JOIN love on p.id=love.post_id"
        # " JOIN user u ON p.author_id = u.id"
        # " GROUP BY p.id"
    ).fetchall()
    return render_template("blog/index.html", posts=posts)


def get_post(id, check_author=True):
    """Get a post and its author by id.

    Checks that the id exists and optionally that the current user is
    the author.

    :param id: id of post to get
    :param check_author: require the current user to be the author
    :return: the post with author information
    :raise 404: if a post with the given id doesn't exist
    :raise 403: if the current user isn't the author
    """
    post = (
        get_db()
        .execute(
            "SELECT p.id, title, body, created, author_id, username"
            " FROM post p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post["author_id"] != g.user["id"]:
        abort(403)

    return post


def post_validation(title):
    if not title:
        return "Title is required."

    if len(title) < 4:
        return "Title name must be bigger than 4 letters."

    if len(title) > 10:
        return "Title cannot be bigger of 10 letters."


@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    """Create a new post for the current user."""
    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = post_validation(title)

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO post (title, body, author_id) VALUES (?, ?, ?)",
                (title, body, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/create.html")


@bp.route("/<int:id>/love", methods=["POST"])
@login_required
def love(id):
    """Create a new post for the current user."""
    db = get_db()
    db.execute(
        "INSERT INTO love (post_id, author_id) VALUES (?, ?)",
        (id, g.user["id"]),
    )
    db.commit()
    return redirect(url_for("blog.index"))


@bp.route("/<int:id>/comment", methods=["POST"])
@login_required
def comment(id):
    if request.method == "POST":
        comment_text = request.form["comment_text"]
        error = None

        if not comment_text:
            return "comment_text is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO comment (comment_text, post_id,  author_id) VALUES (?, ?, ?)",
                (comment_text, id, g.user["id"]),
            )
            db.commit()
            return redirect('details')


@bp.route("/<int:id>/descomment", methods=["POST"])
@login_required
def descomment(id):
    """Delete a comment."""
    if request.method == "POST":
        post_id = request.form["post_id"]
        error = None

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute("DELETE FROM comment WHERE id = ? AND author_id = ?",
                (id, g.user["id"]))
            db.commit()
            return redirect(url_for("blog.index"))

@bp.route("/<int:id>/deslove", methods=["POST"])
@login_required
def deslove(id):
    """Delete a love."""
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM love WHERE post_id = ? AND author_id = ?",
               (id, g.user["id"]))
    db.commit()
    return redirect(url_for("blog.index"))


@bp.route("/<int:id>/update", methods=("GET", "POST"))
@login_required
def update(id):
    """Update a post if the current user is the author."""
    post = get_post(id)

    if request.method == "POST":
        title = request.form["title"]
        body = request.form["body"]
        error = post_validation(title)

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "UPDATE post SET title = ?, body = ? WHERE id = ?", (
                    title, body, id)
            )
            db.commit()
            return redirect(url_for("blog.index"))

    return render_template("blog/update.html", post=post)


@bp.route("/<int:id>/details")
@login_required
def details(id):
    """Update a post if the current user is the author."""
    post = get_post(id)
    
    db = get_db()
    comments = db.execute(
        "SELECT *, u.id as comment_author"
        " FROM comment c"
        " LEFT JOIN user u ON c.author_id = u.id"
        " WHERE c.post_id = ?"
        " GROUP BY c.id"
        " ORDER BY created DESC",
        (id,)
    ).fetchall()

    return render_template("blog/details.html", post=post, comments=comments)


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    """Delete a post.

    Ensures that the post exists and that the logged in user is the
    author of the post.
    """
    get_post(id)
    db = get_db()
    db.execute("DELETE FROM post WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for("blog.index"))
