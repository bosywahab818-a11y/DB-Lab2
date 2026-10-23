import os
import uuid
from pathlib import Path

import bcrypt
import pymysql
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
)
from werkzeug.utils import secure_filename


# ==================== CONFIGURATION ====================

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "AsAS1234@")

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


# ==================== DATABASE CONNECTION ====================

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "AsAS1234@"),
        database=os.getenv("DB_NAME", "library"),
        port=int(os.getenv("DB_PORT", "3306")),
        cursorclass=pymysql.cursors.DictCursor,
    )


# ==================== IMAGE UPLOAD HELPERS ====================

def allowed_file(filename):
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_image(file):
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        raise ValueError("Invalid image format. Use PNG, JPG, JPEG, GIF, or WEBP.")

    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    new_filename = f"{uuid.uuid4().hex}.{extension}"

    destination = UPLOAD_FOLDER / new_filename
    file.save(destination)

    return f"uploads/{new_filename}"


def delete_uploaded_image(image_path):
    if not image_path or not image_path.startswith("uploads/"):
        return

    filename = image_path.split("/", 1)[1]
    file_path = UPLOAD_FOLDER / filename

    try:
        if file_path.is_file():
            file_path.unlink()
    except OSError:
        app.logger.warning("Could not delete image: %s", image_path)


# ==================== HOME ====================

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("todos"))
    return redirect(url_for("login"))


# ==================== REGISTER ====================

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name:
            error = "Name is required"
        elif not email:
            error = "Email is required"
        elif not password:
            error = "Password is required"
        elif not confirm_password:
            error = "Confirm password is required"
        elif password != confirm_password:
            error = "Passwords do not match"
        else:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                    if cursor.fetchone():
                        error = "Email Already Exists"
                    else:
                        password_hash = bcrypt.hashpw(
                            password.encode("utf-8"), bcrypt.gensalt()
                        ).decode("utf-8")

                        cursor.execute(
                            "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                            (email, name, password_hash),
                        )
                        connection.commit()
                        session["user_id"] = cursor.lastrowid
                        session["user_name"] = name
                        return redirect(url_for("todos"))
            finally:
                connection.close()

    return render_template("register.html", error=error)


# ==================== LOGIN ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email:
            error = "Email is required"
        elif not password:
            error = "Password is required"
        else:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT user_id, name, password_hash FROM users WHERE email = %s",
                        (email,),
                    )
                    user = cursor.fetchone()

                    if not user or not bcrypt.checkpw(
                        password.encode("utf-8"), user["password_hash"].encode("utf-8")
                    ):
                        error = "Invalid email or password"
                    else:
                        session.clear()
                        session["user_id"] = user["user_id"]
                        session["user_name"] = user["name"]
                        return redirect(url_for("todos"))
            finally:
                connection.close()

    return render_template("login.html", error=error)


# ==================== LOGOUT ====================

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================== TODOS LIST ====================

@app.route("/todos")
def todos():
    if "user_id" not in session:
        return redirect(url_for("login"))

    current_filter = request.args.get("filter", "all")
    search = request.args.get("search", "").strip()

    if current_filter not in ("all", "open", "done"):
        current_filter = "all"

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            query = "SELECT todo_id, title, is_done, created_at, due_date FROM todos WHERE user_id = %s"
            params = [session["user_id"]]

            if current_filter == "open":
                query += " AND is_done = 0"
            elif current_filter == "done":
                query += " AND is_done = 1"

            if search:
                query += " AND title LIKE %s"
                params.append(f"%{search}%")

            query += " ORDER BY todo_id DESC"
            cursor.execute(query, params)
            todo_items = cursor.fetchall()

            cursor.execute(
                "SELECT COUNT(*) AS open_count FROM todos WHERE user_id = %s AND is_done = 0",
                (session["user_id"],),
            )
            open_count = cursor.fetchone()["open_count"]
    finally:
        connection.close()

    return render_template(
        "todos.html",
        todos=todo_items,
        user_name=session.get("user_name", ""),
        current_filter=current_filter,
        open_count=open_count,
        search=search,
    )


# ==================== ADD TODO ====================

@app.route("/todos/add", methods=["POST"])
def add_todo():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()
    due_date = request.form.get("due_date", "").strip()

    if not title or len(title) > 200:
        return redirect(url_for("todos"))

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO todos (user_id, title, due_date) VALUES (%s, %s, %s)",
                (session["user_id"], title, due_date or None),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("todos"))


# ==================== EDIT TODO ====================

@app.route("/todos/<int:todo_id>/edit", methods=["GET", "POST"])
def edit_todo(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    error = None

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT todo_id, title, due_date FROM todos WHERE todo_id = %s AND user_id = %s",
                (todo_id, session["user_id"]),
            )
            todo = cursor.fetchone()

            if not todo:
                return "Todo not found", 404

            if request.method == "POST":
                title = request.form.get("title", "").strip()
                due_date = request.form.get("due_date", "").strip()

                if not title:
                    error = "Title is required"
                elif len(title) > 200:
                    error = "Title is too long"
                else:
                    cursor.execute(
                        "UPDATE todos SET title = %s, due_date = %s WHERE todo_id = %s AND user_id = %s",
                        (title, due_date or None, todo_id, session["user_id"]),
                    )
                    connection.commit()
                    return redirect(url_for("todos"))

                todo["title"] = title
                todo["due_date"] = due_date or None
    finally:
        connection.close()

    return render_template("edit_todo.html", todo=todo, error=error)


# ==================== DONE / UNDO TODO ====================

@app.route("/todos/<int:todo_id>/done", methods=["POST"])
def toggle_done(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    is_done = request.form.get("is_done", "0")
    if is_done not in ("0", "1"):
        return "Invalid status", 400

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s",
                (int(is_done), todo_id, session["user_id"]),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("todos"))


# ==================== DELETE TODO ====================

@app.route("/todos/<int:todo_id>/delete", methods=["POST"])
def delete_todo(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
                (todo_id, session["user_id"]),
            )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("todos"))


# ==================== LIBRARY ====================

@app.route("/library")
def library():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM AUTHOR ORDER BY author_id")
            authors = cursor.fetchall()

            cursor.execute("SELECT * FROM BOOK ORDER BY book_id")
            books = cursor.fetchall()
    finally:
        connection.close()

    return render_template("library.html", authors=authors, books=books)


# ==================== ADD / EDIT / DELETE AUTHOR ====================

@app.route("/authors/add", methods=["GET", "POST"])
def add_author():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        image = request.files.get("image")
        image_path = None

        if not name:
            return render_template("add_author.html", error="Author name is required")

        try:
            if image and image.filename:
                image_path = save_uploaded_image(image)

            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO AUTHOR (name, country, image_url) VALUES (%s, %s, %s)",
                        (name, country or None, image_path),
                    )
                connection.commit()
            finally:
                connection.close()
            return redirect(url_for("library"))
        except Exception as exc:
            if image_path:
                delete_uploaded_image(image_path)
            return render_template("add_author.html", error=str(exc))

    return render_template("add_author.html")


@app.route("/authors/<int:author_id>/edit", methods=["GET", "POST"])
def edit_author(author_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM AUTHOR WHERE author_id = %s", (author_id,))
            author = cursor.fetchone()

        if not author:
            return "Author not found", 404

        if request.method == "POST":
            name = request.form.get("name", "").strip()
            country = request.form.get("country", "").strip()
            image = request.files.get("image")
            new_image_path = None

            if not name:
                return render_template("edit_author.html", author=author, error="Author name is required")

            if image and image.filename:
                new_image_path = save_uploaded_image(image)

            image_path = new_image_path or author.get("image_url")

            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE AUTHOR SET name = %s, country = %s, image_url = %s WHERE author_id = %s",
                    (name, country or None, image_path, author_id),
                )
            connection.commit()

            if new_image_path and author.get("image_url"):
                delete_uploaded_image(author.get("image_url"))

            return redirect(url_for("library"))
    finally:
        connection.close()

    return render_template("edit_author.html", author=author)


@app.route("/authors/<int:author_id>/delete", methods=["POST"])
def delete_author(author_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT image_url FROM AUTHOR WHERE author_id = %s", (author_id,))
            author = cursor.fetchone()
            image_path = author.get("image_url") if author else None

            cursor.execute("DELETE FROM AUTHOR WHERE author_id = %s", (author_id,))
        connection.commit()
    finally:
        connection.close()

    delete_uploaded_image(image_path)
    return redirect(url_for("library"))


# ==================== ADD / EDIT / DELETE BOOK ====================

@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT author_id, name FROM AUTHOR ORDER BY name")
            authors = cursor.fetchall()

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            price_text = request.form.get("price", "").strip()
            author_id = request.form.get("author_id", "").strip()
            image = request.files.get("image")
            image_path = None

            if not title or not price_text or not author_id:
                return render_template("add_book.html", authors=authors, error="All required fields must be filled")

            price = float(price_text)
            if image and image.filename:
                image_path = save_uploaded_image(image)

            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO BOOK (title, price, author_id, image_url) VALUES (%s, %s, %s, %s)",
                    (title, price, author_id, image_path),
                )
            connection.commit()
            return redirect(url_for("library"))
    finally:
        connection.close()

    return render_template("add_book.html", authors=authors)


@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM BOOK WHERE book_id = %s", (book_id,))
            book = cursor.fetchone()

            cursor.execute("SELECT author_id, name FROM AUTHOR ORDER BY name")
            authors = cursor.fetchall()

        if not book:
            return "Book not found", 404

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            price_text = request.form.get("price", "").strip()
            author_id = request.form.get("author_id", "").strip()
            image = request.files.get("image")
            new_image_path = None

            if not title or not price_text or not author_id:
                return render_template("edit_book.html", book=book, authors=authors, error="All fields are required")

            if image and image.filename:
                new_image_path = save_uploaded_image(image)

            image_path = new_image_path or book.get("image_url")

            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE BOOK SET title = %s, price = %s, author_id = %s, image_url = %s WHERE book_id = %s",
                    (title, float(price_text), author_id, image_path, book_id),
                )
            connection.commit()

            if new_image_path and book.get("image_url"):
                delete_uploaded_image(book.get("image_url"))

            return redirect(url_for("library"))
    finally:
        connection.close()

    return render_template("edit_book.html", book=book, authors=authors)


@app.route("/books/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT image_url FROM BOOK WHERE book_id = %s", (book_id,))
            book = cursor.fetchone()
            image_path = book.get("image_url") if book else None

            cursor.execute("DELETE FROM BOOK WHERE book_id = %s", (book_id,))
        connection.commit()
    finally:
        connection.close()

    delete_uploaded_image(image_path)
    return redirect(url_for("library"))


# ==================== RUN APPLICATION ====================

if __name__ == "__main__":
    app.run(debug=True)