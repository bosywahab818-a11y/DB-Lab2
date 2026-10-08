from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/")
def home():
    return "DB Lab 2 is working!"


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
                    cursor.execute(
                        "SELECT user_id FROM users WHERE email = %s;",
                        (email,)
                    )

                    existing_user = cursor.fetchone()

                    if existing_user:
                        error = "Email Already Exists"
                    else:
                        password_hash = bcrypt.hashpw(
                            password.encode("utf-8"),
                            bcrypt.gensalt()
                        ).decode("utf-8")

                        cursor.execute(
                            """
                            INSERT INTO users
                            (email, name, password_hash)
                            VALUES (%s, %s, %s);
                            """,
                            (email, name, password_hash)
                        )

                        connection.commit()

                        return "Registration successful!"

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
                        """
                        SELECT user_id, name, password_hash
                        FROM users
                        WHERE email = %s;
                        """,
                        (email,)
                    )

                    user = cursor.fetchone()

                    if not user or not bcrypt.checkpw(
                        password.encode("utf-8"),
                        user["password_hash"].encode("utf-8")
                    ):
                        error = "Invalid email or password"
                    else:
                        session["user_id"] = user["user_id"]
                        session["user_name"] = user["name"]

                        return redirect(url_for("todos"))

            finally:
                connection.close()

    return render_template("login.html", error=error)


# ==================== TODOS LIST ====================

@app.route("/todos")
def todos():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT todo_id, title, is_done, created_at
                FROM todos
                WHERE user_id = %s
                ORDER BY todo_id DESC;
                """,
                (session["user_id"],)
            )

            todos = cursor.fetchall()

    finally:
        connection.close()

    return render_template(
        "todos.html",
        todos=todos,
        user_name=session["user_name"]
    )


# ==================== ADD TODO ====================

@app.route("/todos/add", methods=["POST"])
def add_todo():
    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get("title", "").strip()

    if not title:
        return render_template(
            "todos.html",
            todos=[],
            user_name=session["user_name"],
            error="Title is required"
        )

    if len(title) > 200:
        return render_template(
            "todos.html",
            todos=[],
            user_name=session["user_name"],
            error="Title is too long"
        )

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO todos (user_id, title) VALUES (%s, %s);",
                (session["user_id"], title)
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

    try:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT todo_id, title
                FROM todos
                WHERE todo_id = %s AND user_id = %s;
                """,
                (todo_id, session["user_id"])
            )

            todo = cursor.fetchone()

            if not todo:
                return "Todo not found", 404

            error = None

            if request.method == "POST":
                title = request.form.get("title", "").strip()

                if not title:
                    error = "Title is required"

                elif len(title) > 200:
                    error = "Title is too long"

                else:
                    cursor.execute(
                        """
                        UPDATE todos
                        SET title = %s
                        WHERE todo_id = %s AND user_id = %s;
                        """,
                        (title, todo_id, session["user_id"])
                    )

                    connection.commit()

                    return redirect(url_for("todos"))

                todo["title"] = title

    finally:
        connection.close()

    return render_template(
        "edit_todo.html",
        todo=todo,
        error=error
    )

# ==================== DONE / UNDO TODO ====================

@app.route("/todos/<int:todo_id>/done", methods=["POST"])
def toggle_done(todo_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    is_done = request.form.get("is_done", "0")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE todos
                SET is_done = %s
                WHERE todo_id = %s AND user_id = %s;
                """,
                (is_done, todo_id, session["user_id"])
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
                """
                DELETE FROM todos
                WHERE todo_id = %s AND user_id = %s;
                """,
                (todo_id, session["user_id"])
            )

        connection.commit()

    finally:
        connection.close()

    return redirect(url_for("todos"))
# ==================== LOGOUT ====================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==================== RUN APP ====================

if __name__ == "__main__":
    app.run(debug=True)