from flask import Flask, redirect, render_template , request, g
import uuid
from cs50 import SQL



app = Flask(__name__)
db = SQL("sqlite:///planit.db")

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/newtrip", methods=["GET", "POST"])
def createtrip():
    if request.method == "GET":
        return render_template("createatrip.html")
    else:
        location = request.form["location"]
        name = request.form["name"]
        date = request.form["date"]
        id = str(uuid.uuid1())
        db.execute("INSERT INTO tbl_tripgroupe (date, location, , name) VALUES (%s , %s, %s, %s)", (date, location, id, name))
        return render_template("sharelink.html", trip_id = id)
    

@app.route("/jointrip", methods=["GET", "POST"])
def jointrip():
    return render_template("jointrip.html")

@app.route("/generatetrip", methods=["POST"])
def generate():
    return render_template("plan.html")

@app.route("/plandetails", methods=["POST"])
def plandetails():
    return render_template("plandetails.html")


@app.route("/dashboard", methods=["GET", "POST"])
def message():
    return render_template("message.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")



