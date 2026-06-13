from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "expense_tracker_secret"


# -------------------------
# DATABASE
# -------------------------
def get_connection():
    return sqlite3.connect("expense.db")


def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS budget(
        category TEXT PRIMARY KEY,
        amount REAL
    )
    """)

    conn.commit()
    conn.close()


# -------------------------
# LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM users
        WHERE username=?
        AND password=?
        """,
        (username, password))

        user = cursor.fetchone()

        conn.close()

        if user:
            session["user"] = username
            return redirect("/")

    return render_template("login.html")


# -------------------------
# REGISTER
# -------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()

        try:

            cursor.execute("""
            INSERT INTO users
            (username,password)
            VALUES (?,?)
            """,
            (username, password))

            conn.commit()

        except:
            pass

        conn.close()

        return redirect("/login")

    return render_template("register.html")


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# -------------------------
# HOME DASHBOARD
# -------------------------
@app.route("/")
def home():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT SUM(amount) FROM expenses"
    )

    total = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT COUNT(*) FROM expenses"
    )

    count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT AVG(amount) FROM expenses"
    )

    average = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT MAX(amount) FROM expenses"
    )

    highest = cursor.fetchone()[0] or 0

    conn.close()

    return render_template(
        "home.html",
        total=round(total, 2),
        count=count,
        average=round(average, 2),
        highest=round(highest, 2)
    )


# -------------------------
# ADD EXPENSE
# -------------------------
@app.route("/add", methods=["GET", "POST"])
def add_expense():

    if request.method == "POST":

        expense_date = request.form["date"]
        category = request.form["category"]
        description = request.form["description"]
        amount = float(
            request.form["amount"]
        )

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO expenses
        (
            date,
            category,
            description,
            amount
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            expense_date,
            category,
            description,
            amount
        ))

        conn.commit()

        # Budget Check

        cursor.execute("""
        SELECT amount
        FROM budget
        WHERE category=?
        """,
        (category,))

        budget = cursor.fetchone()

        if budget:

            limit = budget[0]

            cursor.execute("""
            SELECT SUM(amount)
            FROM expenses
            WHERE category=?
            """,
            (category,))

            spent = cursor.fetchone()[0] or 0

            if spent > limit:

                print(
                    f"Budget Exceeded for {category}"
                )

        conn.close()

        return redirect("/expenses")

    return render_template(
        "add_expense.html"
    )


# -------------------------
# VIEW EXPENSES
# -------------------------
@app.route("/expenses")
def expenses():

    search = request.args.get(
        "search",
        ""
    )

    from_date = request.args.get(
        "from_date",
        ""
    )

    to_date = request.args.get(
        "to_date",
        ""
    )

    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT *
    FROM expenses
    WHERE 1=1
    """

    params = []

    if search:

        query += """
        AND (
            category LIKE ?
            OR description LIKE ?
        )
        """

        params.extend([
            f"%{search}%",
            f"%{search}%"
        ])

    if from_date and to_date:

        query += """
        AND date BETWEEN ? AND ?
        """

        params.extend([
            from_date,
            to_date
        ])

    query += """
    ORDER BY date DESC
    """

    cursor.execute(
        query,
        params
    )

    rows = cursor.fetchall()

    conn.close()

    total = sum(
        row[4]
        for row in rows
    )

    return render_template(
        "expenses.html",
        expenses=rows,
        total=total,
        search=search,
        from_date=from_date,
        to_date=to_date
    )


# -------------------------
# EDIT
# -------------------------
@app.route("/edit/<int:id>",
           methods=["GET", "POST"])
def edit_expense(id):

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        expense_date = request.form["date"]
        category = request.form["category"]
        description = request.form["description"]
        amount = float(
            request.form["amount"]
        )

        cursor.execute("""
        UPDATE expenses
        SET
            date=?,
            category=?,
            description=?,
            amount=?
        WHERE id=?
        """,
        (
            expense_date,
            category,
            description,
            amount,
            id
        ))

        conn.commit()
        conn.close()

        return redirect("/expenses")

    cursor.execute(
        """
        SELECT *
        FROM expenses
        WHERE id=?
        """,
        (id,)
    )

    expense = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_expense.html",
        expense=expense
    )


# -------------------------
# DELETE
# -------------------------
@app.route("/delete/<int:id>")
def delete_expense(id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE
        FROM expenses
        WHERE id=?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/expenses")




# -------------------------
# CATEGORY SUMMARY
# -------------------------
@app.route("/summary")
def summary():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        category,
        SUM(amount)
    FROM expenses
    GROUP BY category
    ORDER BY SUM(amount) DESC
    """)

    summary_data = cursor.fetchall()

    conn.close()

    return render_template(
        "summary.html",
        summary=summary_data
    )

# -------------------------
# MONTHLY ANALYTICS
# -------------------------
@app.route("/monthly")
def monthly():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        substr(date,1,7),
        SUM(amount)
    FROM expenses
    GROUP BY substr(date,1,7)
    ORDER BY substr(date,1,7)
    """)

    monthly_data = cursor.fetchall()

    conn.close()

    return render_template(
        "monthly.html",
        monthly_data=monthly_data
    )
# -------------------------
# BUDGET
# -------------------------
@app.route("/budget", methods=["GET", "POST"])
def budget():

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":

        category = request.form["category"]
        amount = float(request.form["budget"])

        cursor.execute("""
        INSERT OR REPLACE INTO budget
        VALUES (?, ?)
        """, (category, amount))

        conn.commit()

    cursor.execute("""
    SELECT *
    FROM budget
    """)

    budgets = cursor.fetchall()

    conn.close()

    return render_template(
        "budget.html",
        budgets=budgets
    )

# -------------------------
# PIE CHART
# -------------------------
@app.route("/chart")
def chart():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        category,
        SUM(amount)
    FROM expenses
    GROUP BY category
    """)

    data = cursor.fetchall()

    conn.close()

    if len(data) == 0:
        return "No expense data available"

    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    plt.figure(figsize=(8,6))

    plt.pie(
        amounts,
        labels=categories,
        autopct="%1.1f%%"
    )

    plt.title("Expense Distribution")

    os.makedirs("static", exist_ok=True)

    plt.savefig("static/chart.png")

    plt.close()

    return render_template("chart.html")
# -------------------------
# TEST DATABASE
# -------------------------
@app.route("/test")
def test():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM expenses"
    )

    rows = cursor.fetchall()

    conn.close()

    return str(rows)


# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":

    init_db()

    app.run(debug=True)