import json
import os
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
TODOS_FILE = os.path.join(os.path.dirname(__file__), "todos.json")


def load_todos():
    if not os.path.exists(TODOS_FILE):
        return []
    with open(TODOS_FILE, "r") as f:
        return json.load(f)


def save_todos(todos):
    with open(TODOS_FILE, "w") as f:
        json.dump(todos, f, indent=2)


@app.route("/")
def index():
    todos = load_todos()
    return render_template("index.html", todos=todos)


@app.route("/add", methods=["POST"])
def add():
    text = request.form.get("text", "").strip()
    if text:
        todos = load_todos()
        new_id = max((t["id"] for t in todos), default=0) + 1
        todos.append({"id": new_id, "text": text, "done": False})
        save_todos(todos)
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = not todo["done"]
            break
    save_todos(todos)
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    todos = load_todos()
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
