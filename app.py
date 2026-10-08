from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")


# ==================== DATABASE CONNECTION ====================

def get_db_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        cursorclass=pymysql.cursors.DictCursor
    )


# ==================== HOME ====================

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
                        """
                        SELECT user_id
                        FROM users
                        WHERE email = %s;
                        """,
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

                        cursor.execute("""
                        INSERT INTO users
                        (email, name, password_hash)
                         VALUES (%s, %s, %s);
                          """,
                        (email, name, password_hash))

                        connection.commit()
                        session["user_id"] = cursor.lastrowid
                        session["user_name"] = name
                        connection.commit()
                        return redirect(url_for("todos"))


            finally:
                connection.close()

    return render_template(
        "register.html",
        error=error
    )


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

    return render_template(
        "login.html",
        error=error
    )


# ==================== TODOS LIST ====================

@app.route("/todos")
def todos():

    if "user_id" not in session:
        return redirect(url_for("login"))

    current_filter = request.args.get(
        "filter",
        "all"
    )

    search = request.args.get(
        "search",
        ""
    ).strip()

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            # Base query

            query = """
                SELECT
                    todo_id,
                    title,
                    is_done,
                    created_at,
                    due_date
                FROM todos
                WHERE user_id = %s
            """

            params = [
                session["user_id"]
            ]

            # ==================== FILTER ====================

            if current_filter == "open":

                query += """
                    AND is_done = 0
                """

            elif current_filter == "done":

                query += """
                    AND is_done = 1
                """

            else:

                current_filter = "all"

            # ==================== SEARCH ====================

            if search:

                query += """
                    AND title LIKE %s
                """

                params.append(
                    f"%{search}%"
                )

            # ==================== ORDER ====================

            query += """
                ORDER BY todo_id DESC;
            """

            cursor.execute(
                query,
                params
            )

            todos = cursor.fetchall()

            # ==================== OPEN COUNT ====================

            cursor.execute(
                """
                SELECT COUNT(*) AS open_count
                FROM todos
                WHERE user_id = %s
                AND is_done = 0;
                """,
                (session["user_id"],)
            )

            open_count = cursor.fetchone()[
                "open_count"
            ]

    finally:

        connection.close()

    return render_template(
        "todos.html",
        todos=todos,
        user_name=session["user_name"],
        current_filter=current_filter,
        open_count=open_count,
        search=search
    )


# ==================== ADD TODO ====================

@app.route("/todos/add", methods=["POST"])
def add_todo():

    if "user_id" not in session:
        return redirect(url_for("login"))

    title = request.form.get(
        "title",
        ""
    ).strip()

    due_date = request.form.get(
        "due_date",
        ""
    ).strip()

    # ==================== VALIDATION ====================

    if not title:

        return render_template(
            "todos.html",
            todos=[],
            user_name=session["user_name"],
            error="Title is required",
            current_filter="all",
            open_count=0,
            search=""
        )

    if len(title) > 200:

        return render_template(
            "todos.html",
            todos=[],
            user_name=session["user_name"],
            error="Title is too long",
            current_filter="all",
            open_count=0,
            search=""
        )

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO todos
                (user_id, title, due_date)
                VALUES (%s, %s, %s);
                """,
                (
                    session["user_id"],
                    title,
                    due_date if due_date else None
                )
            )

        connection.commit()

    finally:

        connection.close()

    return redirect(
        url_for("todos")
    )


# ==================== EDIT TODO ====================

@app.route(
    "/todos/<int:todo_id>/edit",
    methods=["GET", "POST"]
)
def edit_todo(todo_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    todo_id,
                    title,
                    due_date
                FROM todos
                WHERE todo_id = %s
                AND user_id = %s;
                """,
                (
                    todo_id,
                    session["user_id"]
                )
            )

            todo = cursor.fetchone()

            if not todo:

                return "Todo not found", 404

            error = None

            # ==================== POST ====================

            if request.method == "POST":

                title = request.form.get(
                    "title",
                    ""
                ).strip()

                due_date = request.form.get(
                    "due_date",
                    ""
                ).strip()

                if not title:

                    error = "Title is required"

                elif len(title) > 200:

                    error = "Title is too long"

                else:

                    cursor.execute(
                        """
                        UPDATE todos
                        SET
                            title = %s,
                            due_date = %s
                        WHERE todo_id = %s
                        AND user_id = %s;
                        """,
                        (
                            title,
                            due_date if due_date else None,
                            todo_id,
                            session["user_id"]
                        )
                    )

                    connection.commit()

                    return redirect(
                        url_for("todos")
                    )

                todo["title"] = title
                todo["due_date"] = due_date

    finally:

        connection.close()

    return render_template(
        "edit_todo.html",
        todo=todo,
        error=error
    )


# ==================== DONE / UNDO TODO ====================

@app.route(
    "/todos/<int:todo_id>/done",
    methods=["POST"]
)
def toggle_done(todo_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    is_done = request.form.get(
        "is_done",
        "0"
    )

    # Validate status

    if is_done not in ("0", "1"):

        return "Invalid status", 400

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE todos
                SET is_done = %s
                WHERE todo_id = %s
                AND user_id = %s;
                """,
                (
                    is_done,
                    todo_id,
                    session["user_id"]
                )
            )

        connection.commit()

    finally:

        connection.close()

    return redirect(
        url_for("todos")
    )


# ==================== DELETE TODO ====================

@app.route(
    "/todos/<int:todo_id>/delete",
    methods=["POST"]
)
def delete_todo(todo_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    try:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM todos
                WHERE todo_id = %s
                AND user_id = %s;
                """,
                (
                    todo_id,
                    session["user_id"]
                )
            )

        connection.commit()

    finally:

        connection.close()

    return redirect(
        url_for("todos")
    )


# ==================== LOGOUT ====================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ==================== RUN APP ====================

if __name__ == "__main__":

    app.run(
        debug=True
    )