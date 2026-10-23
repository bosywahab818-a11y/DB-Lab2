import io
import unittest
import uuid
import pymysql
import bcrypt

from app import app, get_db_connection


class BasicAppTests(unittest.TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

        self.client = app.test_client()

        self.test_email = (
            f"test_{uuid.uuid4().hex[:8]}@example.com"
        )

        self.test_password = "TestPassword123!"

        self.test_user_id = None
        self.test_todo_id = None
        self.test_author_id = None
        self.test_book_id = None

        self.create_test_user()

    # ==================================================
    # CREATE TEST USER
    # ==================================================

    def create_test_user(self):
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                password_hash = bcrypt.hashpw(
                    self.test_password.encode("utf-8"),
                    bcrypt.gensalt()
                ).decode("utf-8")

                cursor.execute(
                    """
                    INSERT INTO users
                    (email, name, password_hash)
                    VALUES (%s, %s, %s);
                    """,
                    (
                        self.test_email,
                        "Automated Test User",
                        password_hash
                    )
                )

                self.test_user_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # LOGIN TEST USER
    # ==================================================

    def login_test_user(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.test_user_id
            session["user_name"] = "Automated Test User"

    # ==================================================
    # CREATE TEST TODO
    # ==================================================

    def create_test_todo(
        self,
        title="Test Todo",
        due_date=None
    ):
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
                        self.test_user_id,
                        title,
                        due_date
                    )
                )

                todo_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

        self.test_todo_id = todo_id

        return todo_id

    # ==================================================
    # CLEAN DATABASE AFTER EACH TEST
    # ==================================================

    def tearDown(self):
        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM todos
                    WHERE user_id = %s;
                    """,
                    (self.test_user_id,)
                )

                cursor.execute(
                    """
                    DELETE FROM users
                    WHERE user_id = %s;
                    """,
                    (self.test_user_id,)
                )

                if self.test_author_id:
                    cursor.execute(
                        """
                        DELETE FROM AUTHOR
                        WHERE author_id = %s;
                        """,
                        (self.test_author_id,)
                    )

                if self.test_book_id:
                    cursor.execute(
                        """
                        DELETE FROM BOOK
                        WHERE book_id = %s;
                        """,
                        (self.test_book_id,)
                    )

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # BASIC TESTS
    # ==================================================

    def test_home_page(self):
        response = self.client.get("/")

        self.assertEqual(
            response.status_code,
            302
        )

    def test_login_page(self):
        response = self.client.get("/login")

        self.assertEqual(
            response.status_code,
            200
        )

    def test_register_page(self):
        response = self.client.get("/register")

        self.assertEqual(
            response.status_code,
            200
        )

    def test_todos_requires_login(self):
        response = self.client.get("/todos")

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/login",
            response.location
        )

    # ==================================================
    # REGISTER TESTS
    # ==================================================

    def test_register_duplicate_email(self):
        response = self.client.post(
            "/register",
            data={
                "name": "Another User",
                "email": self.test_email,
                "password": "AnotherPassword123!",
                "confirm_password": "AnotherPassword123!"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Email Already Exists",
            response.data
        )

    def test_register_password_mismatch(self):
        response = self.client.post(
            "/register",
            data={
                "name": "New User",
                "email": (
                    f"new_{uuid.uuid4().hex[:8]}"
                    "@example.com"
                ),
                "password": "Password123!",
                "confirm_password": "DifferentPassword123!"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Passwords do not match",
            response.data
        )

    # ==================================================
    # LOGIN TESTS
    # ==================================================

    def test_login_correct_password(self):
        response = self.client.post(
            "/login",
            data={
                "email": self.test_email,
                "password": self.test_password
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/todos",
            response.location
        )

        with self.client.session_transaction() as session:
            self.assertEqual(
                session["user_id"],
                self.test_user_id
            )

    def test_login_wrong_password(self):
        response = self.client.post(
            "/login",
            data={
                "email": self.test_email,
                "password": "WrongPassword123!"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Invalid email or password",
            response.data
        )

    def test_login_unknown_email(self):
        response = self.client.post(
            "/login",
            data={
                "email": "doesnotexist@example.com",
                "password": "Password123!"
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Invalid email or password",
            response.data
        )

    # ==================================================
    # LOGOUT TEST
    # ==================================================

    def test_logout(self):
        with self.client.session_transaction() as session:
            session["user_id"] = self.test_user_id
            session["user_name"] = "Automated Test User"

        response = self.client.get("/logout")

        self.assertEqual(
            response.status_code,
            302
        )

        with self.client.session_transaction() as session:
            self.assertNotIn(
                "user_id",
                session
            )

    # ==================================================
    # ADD TODO
    # ==================================================

    def test_add_todo(self):
        self.login_test_user()

        response = self.client.post(
            "/todos/add",
            data={
                "title": "Buy groceries",
                "due_date": ""
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.assertIn(
            "/todos",
            response.location
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT title, is_done
                    FROM todos
                    WHERE user_id = %s
                    ORDER BY todo_id DESC
                    LIMIT 1;
                    """,
                    (self.test_user_id,)
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertIsNotNone(todo)

        self.assertEqual(
            todo["title"],
            "Buy groceries"
        )

        self.assertEqual(
            todo["is_done"],
            0
        )

    # ==================================================
    # ADD TODO WITH DUE DATE
    # ==================================================

    def test_add_todo_with_due_date(self):
        self.login_test_user()

        response = self.client.post(
            "/todos/add",
            data={
                "title": "Submit project",
                "due_date": "2026-12-31"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT title, due_date
                    FROM todos
                    WHERE user_id = %s
                    ORDER BY todo_id DESC
                    LIMIT 1;
                    """,
                    (self.test_user_id,)
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertEqual(
            todo["title"],
            "Submit project"
        )

        self.assertEqual(
            str(todo["due_date"]),
            "2026-12-31"
        )

    # ==================================================
    # EDIT TODO
    # ==================================================

    def test_edit_todo(self):
        self.login_test_user()

        todo_id = self.create_test_todo(
            title="Old title"
        )

        response = self.client.post(
            f"/todos/{todo_id}/edit",
            data={
                "title": "Updated title",
                "due_date": "2026-11-30"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT title, due_date
                    FROM todos
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertIsNotNone(todo)

        self.assertEqual(
            todo["title"],
            "Updated title"
        )

        self.assertEqual(
            str(todo["due_date"]),
            "2026-11-30"
        )

    # ==================================================
    # MARK TODO AS DONE
    # ==================================================

    def test_mark_todo_done(self):
        self.login_test_user()

        todo_id = self.create_test_todo()

        response = self.client.post(
            f"/todos/{todo_id}/done",
            data={
                "is_done": "1"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT is_done
                    FROM todos
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertEqual(
            todo["is_done"],
            1
        )

    # ==================================================
    # UNDO TODO
    # ==================================================

    def test_undo_todo(self):
        self.login_test_user()

        todo_id = self.create_test_todo()

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE todos
                    SET is_done = 1
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

            connection.commit()

        finally:
            connection.close()

        response = self.client.post(
            f"/todos/{todo_id}/done",
            data={
                "is_done": "0"
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT is_done
                    FROM todos
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertEqual(
            todo["is_done"],
            0
        )

    # ==================================================
    # DELETE TODO
    # ==================================================

    def test_delete_todo(self):
        self.login_test_user()

        todo_id = self.create_test_todo(
            title="Todo to delete"
        )

        response = self.client.post(
            f"/todos/{todo_id}/delete"
        )

        self.assertEqual(
            response.status_code,
            302
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT todo_id
                    FROM todos
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

                todo = cursor.fetchone()

        finally:
            connection.close()

        self.assertIsNone(todo)

    # ==================================================
    # SEARCH TODOS
    # ==================================================

    def test_search_todos(self):
        self.login_test_user()

        self.create_test_todo(
            title="Study Database"
        )

        response = self.client.get(
            "/todos?search=Database"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Study Database",
            response.data
        )

    # ==================================================
    # OPEN FILTER
    # ==================================================

    def test_open_filter(self):
        self.login_test_user()

        todo_id = self.create_test_todo(
            title="Open Todo"
        )

        response = self.client.get(
            "/todos?filter=open"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Open Todo",
            response.data
        )

    # ==================================================
    # DONE FILTER
    # ==================================================

    def test_done_filter(self):
        self.login_test_user()

        todo_id = self.create_test_todo(
            title="Completed Todo"
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE todos
                    SET is_done = 1
                    WHERE todo_id = %s
                    AND user_id = %s;
                    """,
                    (
                        todo_id,
                        self.test_user_id
                    )
                )

            connection.commit()

        finally:
            connection.close()

        response = self.client.get(
            "/todos?filter=done"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Completed Todo",
            response.data
        )

    # ==================================================
    # OWNERSHIP PROTECTION
    # ==================================================

    def test_cannot_edit_another_users_todo(self):
        self.login_test_user()

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO users
                    (email, name, password_hash)
                    VALUES (%s, %s, %s);
                    """,
                    (
                        f"owner_{uuid.uuid4().hex[:8]}@example.com",
                        "Other User",
                        "dummy_hash"
                    )
                )

                other_user_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO todos
                    (user_id, title)
                    VALUES (%s, %s);
                    """,
                    (
                        other_user_id,
                        "Other User Todo"
                    )
                )

                other_todo_id = cursor.lastrowid

            connection.commit()

        finally:
            connection.close()

        response = self.client.post(
            f"/todos/{other_todo_id}/edit",
            data={
                "title": "Hacked Todo",
                "due_date": ""
            }
        )

        self.assertEqual(
            response.status_code,
            404
        )

        connection = get_db_connection()

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM todos
                    WHERE todo_id = %s;
                    """,
                    (other_todo_id,)
                )

                cursor.execute(
                    """
                    DELETE FROM users
                    WHERE user_id = %s;
                    """,
                    (other_user_id,)
                )

            connection.commit()

        finally:
            connection.close()

    # ==================================================
    # LAB 3 LIBRARY TESTS (AUTHORS, BOOKS & UPLOADS)
    # ==================================================

    def test_library_page(self):
        response = self.client.get("/library")

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertIn(
            b"Library Management System",
            response.data
        )

    def test_add_and_edit_author_routes(self):
        # 1. GET Add Author Page
        get_res = self.client.get("/authors/add")
        self.assertEqual(get_res.status_code, 200)

        # 2. POST Add Author
        post_res = self.client.post(
            "/authors/add",
            data={
                "name": "Dedicated Form Author",
                "country": "Egypt"
            }
        )
        self.assertEqual(post_res.status_code, 302)

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT author_id, country FROM AUTHOR WHERE name = %s;",
                    ("Dedicated Form Author",)
                )
                author = cursor.fetchone()
        finally:
            connection.close()

        self.assertIsNotNone(author)
        self.test_author_id = author["author_id"]

        # 3. GET Edit Author Page
        edit_get = self.client.get(f"/authors/{self.test_author_id}/edit")
        self.assertEqual(edit_get.status_code, 200)

        # 4. POST Edit Author
        edit_post = self.client.post(
            f"/authors/{self.test_author_id}/edit",
            data={
                "name": "Updated Author Name",
                "country": "UK"
            }
        )
        self.assertEqual(edit_post.status_code, 302)

    def test_delete_author_cascades_books(self):
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO AUTHOR (name, country) VALUES (%s, %s);",
                    ("Cascade Parent", "Egypt")
                )
                author_id = cursor.lastrowid

                cursor.execute(
                    "INSERT INTO BOOK (title, price, author_id) VALUES (%s, %s, %s);",
                    ("Cascade Child Book", 10.00, author_id)
                )
                book_id = cursor.lastrowid
            connection.commit()
        finally:
            connection.close()

        # Delete Author
        self.client.post(f"/authors/{author_id}/delete")

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM BOOK WHERE book_id = %s;", (book_id,))
                book = cursor.fetchone()
        finally:
            connection.close()

        self.assertIsNone(book)

    def test_author_image_upload(self):
        image_file = (io.BytesIO(b"test buffer"), "author_photo.png")

        response = self.client.post(
            "/authors/add",
            data={
                "name": "Upload Test Author",
                "country": "France",
                "image": image_file
            },
            content_type="multipart/form-data"
        )
        self.assertEqual(response.status_code, 302)


if __name__ == "__main__":
    unittest.main()