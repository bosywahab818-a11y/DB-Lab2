# Login & To-Do Application

## Team Members

- Bouthina Mohamed Abdelwahab
- Student ID: 2304065

## Project Overview

A simple web-based Login and To-Do application built for the Database Systems Lab.

The application allows users to:

- Create an account
- Login and logout
- Add todos
- Edit todos
- Mark todos as done or undone
- Delete todos
- View only their own todos

## Tech Stack

- Python
- Flask
- MySQL
- PyMySQL
- HTML
- CSS
- JavaScript
- bcrypt
- python-dotenv

## Database

The application uses a MySQL database called `registration`.

It contains two tables:

- `users`
- `todos`

The relationship between the tables is implemented using a Foreign Key:

```sql
FOREIGN KEY (user_id) REFERENCES users(user_id)