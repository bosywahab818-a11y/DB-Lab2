# Database Systems Lab 3: Foreign Keys & Library Application

## Team Members

- **Name:** Bouthina Mohamed Abdelwahab 
- **Student ID:** 2304065

- **Name:** Hana Ahmed Shehata 
- **Student ID:** 2304081

---

## Project Overview

This repository contains deliverables for **Lab 3: Foreign Keys and Simple SQL**.

The project consists of two core parts:
1. **Problem 1 (COMPANY Database):** Relational schema implementation, foreign key constraint demonstrations, and question responses.
2. **Problem 2 (Library & To-Do Application):** A full-stack Flask web application extended from Lab 2 to support full multi-page CRUD operations on Authors and Books, complete with direct file upload functionality for author photos and book covers (Bonus feature).

---

## Web Application Architecture & Features

### Architecture Update
The application has transitioned from inline table editing to a multi-page UI architecture with dedicated forms for adding and editing records.

### To-Do System (Lab 2)
- User registration and login authentication (with `bcrypt` password hashing).
- Protected personal To-Do list with status toggling (`open`/`done`), due dates, and search filtering.
- Navigation link to switch directly to the Library Management System.

### Library Management System (Lab 3)
- **View Data (F2.1):** Display structured HTML tables listing all Authors and Books on `/library`.
- **Add Entities (F2.2):** Dedicated form pages (`/authors/add` and `/books/add`) to create authors and books.
- **Edit Entities (F2.3):** Dedicated form pages (`/authors/<id>/edit` and `/books/<id>/edit`) to modify existing authors or update book details (including changing associated authors).
- **Delete Entities (F2.4 & F2.5):** Remove books or authors with `ON DELETE CASCADE` support (deleting an author automatically removes all associated books).
- **Image File Uploads (Bonus):** Local image file handling using `multipart/form-data`. Uploaded files are renamed using unique identifiers (`UUID`) and saved directly into `website/static/uploads/`. Old image files are automatically cleaned up upon updates or deletions.

---

## Project Structure

```text
lab3-2304065/
├── problem1_DDL.sql         # DDL script for COMPANY schema
├── problem1_DML.sql         # Insert seed data for COMPANY schema
├── problem1_Answers.txt     # Question responses and SQL execution outputs
├── problem2_DDL.sql         # DDL script for Library schema (users, todos, AUTHOR, BOOK)
├── problem2_DML.sql         # Insert seed data for Library schema
├── README.md                # Project documentation
└── website/
    ├── app.py               # Main Flask server application & routes
    ├── test_app.py          # Automated unit tests suite
    ├── .env                 # Database configuration file
    ├── static/
    │   ├── style.css        # CSS styles
    │   └── uploads/         # Direct image upload destination
    └── templates/
        ├── library.html     # Main Library System UI
        ├── add_author.html  # Dedicated form to add author
        ├── edit_author.html # Dedicated form to edit author
        ├── add_book.html    # Dedicated form to add book
        ├── edit_book.html   # Dedicated form to edit book
        ├── todos.html       # To-Do list UI
        ├── edit_todo.html   # To-Do editor UI
        ├── login.html       # Login page UI
        └── register.html    # Registration page UI
```

---

## Database Schemas

### 1. COMPANY Database (`company`)
- `EMPLOYEE` (ssn, fname, lname, bdate, address, gender, salary, Dno)
- `DEPARTMENT` (Dnumber, Dname, mgr_ssn, mgr_start_date)
- `PROJECT` (Pnumber, Pname, Plocation, Dno)

### 2. Library Database (`library`)
- `users` (user_id, name, email, password_hash, created_at)
- `todos` (todo_id, user_id, title, is_done, due_date, created_at)
- `AUTHOR` (author_id, name, country, image_url)
- `BOOK` (book_id, title, price, author_id, image_url)
  - **Foreign Key:** `BOOK.author_id` references `AUTHOR.author_id` with `ON DELETE CASCADE`.

---

## How to Run the Project & Tests

### Step 1: Database Setup
Execute the DDL and DML scripts in MySQL Workbench or MySQL CLI:

```sql
-- Problem 1
SOURCE problem1_DDL.sql;
SOURCE problem1_DML.sql;

-- Problem 2
SOURCE problem2_DDL.sql;
SOURCE problem2_DML.sql;
```

### Step 2: Environment Setup
Ensure your `website/.env` file contains your local MySQL server credentials:

```ini
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=library
DB_PORT=3306
SECRET_KEY=your_secret_key
```

### Step 3: Run Application
Navigate to the `website/` directory and start Flask:

```bash
cd website
python app.py
```

Access the app in your browser at:
- **Library System:** [http://127.0.0.1:5000/library](http://127.0.0.1:5000/library)
- **To-Do Application:** [http://127.0.0.1:5000/todos](http://127.0.0.1:5000/todos)

### Step 4: Run Unit Tests
To run the automated test suite, navigate into `website/` and run `test_app.py`:

```bash
cd website
python test_app.py
```

---

## Lab Questions & Answers (Problem 1 & 2)

### (a) Delete referenced row in EMPLOYEE
Deleting an `EMPLOYEE` record referenced by `DEPARTMENT.mgr_ssn` triggers an `ERROR 1451 (23000): Cannot delete or update a parent row: a foreign key constraint fails` error, preventing orphan references.

### (b) Insert row in PROJECT referencing non-existent DEPARTMENT
Inserting a `PROJECT` with a `Dno` that does not exist in `DEPARTMENT` triggers an `ERROR 1452 (23000): Cannot add or update a child row: a foreign key constraint fails` error.

### (c) Mutual NOT NULL foreign keys
When two tables reference each other with `NOT NULL` columns, insert the first records by temporarily disabling foreign key checks (`SET FOREIGN_KEY_CHECKS = 0;`), inserting both rows, and re-enabling checks (`SET FOREIGN_KEY_CHECKS = 1;`).

### (d) Why do UPDATE and DELETE contain `AND user_id = %s`?
It provides an authorization check ensuring that users can only modify or delete their own To-Dos stored in session. Removing it would allow users to tamper with others' data by guessing the `todo_id`.