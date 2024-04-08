from flask import Flask, redirect, render_template , request, g, session
from flask_session import Session
import uuid
from cs50 import SQL
import googlemaps
import pprint
import time, os
from ApiKeys import get_my_map_key, get_my_openai_key
from openai import OpenAI
import os
import json


app = Flask(__name__)
db = SQL("sqlite:///planit.db")

MAP_API_KEY = get_my_map_key()
OPENAI_API_KEY = get_my_openai_key()

gmaps = googlemaps.Client(key = MAP_API_KEY)

client = OpenAI(
    api_key=OPENAI_API_KEY
)


app.secret_key = os.urandom(100000000)
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config['PERMANENT_SESSION_LIFETIME'] = 86400

app.config["places"] = ""



@app.route("/", methods=["GET", "POST"])
def index():
    if session.get("userid") is None:
        return redirect("/login")
    else:
        return render_template("index.html")

@app.route("/plandetails/<name>", methods=["GET", "POST"])
def plandetails(name):
    if session.get("userid") is None:
        return redirect("/login")
    else:
            names = name.split(",")
            print(name[0])
            events = db.execute("SELECT events FROM tbl_groupchats WHERE name = ?", (names[0]))
            json_formatted_str = events[0]["events"].replace("'", '"')
            data = json.loads(json_formatted_str)
            print(data)
            for foo in data:
                if foo["name"] == names[1]:
                    return render_template("plandetails.html", event = foo)
            
            return redirect("/")
            

@app.route("/dashboard", methods=["GET", "POST"])
def message():
    if session.get("userid") is None:
        return redirect("/login")
    else:
        if request.method == "GET":
            groupchats = db.execute("SELECT groupchats FROM tbl_user WHERE userid = ?", (session.get('userid'),))
            
            groupchats = groupchats[0]["groupchats"]

            groups = groupchats.split(",")

            return render_template("dashboard.html", show_group = True, groups = groups)

@app.route("/dashboard/<name>", methods=["GET", "POST"])
def dashboardname(name):
    if session.get("userid") is None:
        return redirect("/login")
    else:
        if request.method == "GET":
            is_done = db.execute(f"SELECT profile_done FROM tbl_{name} WHERE userid = ?", (session.get('userid'),))
            if is_done[0]['profile_done'] != "True":
                group_id = db.execute(f"SELECT inviteid FROM tbl_groupchats WHERE name = ?", (name))
                return redirect(f"/profile/{group_id[0]['inviteid']}")
            else:
                profiles = db.execute(f"SELECT profile_done FROM tbl_{name}")
                for profile in profiles:
                    if profile['profile_done'] != "True":
                        return render_template("dashboard.html", show_wait = True)
                gen_events = db.execute("SELECT events FROM tbl_groupchats WHERE name = ?", (name))
                if not gen_events[0]["events"]:
                    food_places = GenerateFoodPlaces(name)
                    activity_places = GenerateActivityPlaces(name)
                    events = GenerateEvents(food_places, activity_places)
                    db.execute("UPDATE tbl_groupchats SET events = ? WHERE name = ?", str(events), name)
                    db.execute("UPDATE tbl_groupchats SET resto = ? WHERE name = ?", str(food_places), name)
                    db.execute("UPDATE tbl_groupchats SET activities = ? WHERE name = ?", str(activity_places), name)

                    return render_template("dashboard.html", show_results = True, events = events, name=name)
                else:
                    events = db.execute("SELECT events FROM tbl_groupchats WHERE name = ?", (name))
                    json_formatted_str = events[0]["events"].replace("'", '"')
                    data = json.loads(json_formatted_str)
                    return render_template("dashboard.html", show_results = True, events = data, name=name)
        else:
            return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
   if request.method == "GET":
        return render_template("login.html")
   else:
        session.clear()
        name = request.form["name"]
        password = request.form["password"]
        userid = db.execute("SELECT userid FROM tbl_user WHERE name = ? AND password = ?", name, password)
        if not userid:
            print("wrong password")
            return redirect("/login.html")
        else:
            session["userid"] = userid[0]["userid"]
            return redirect("/")

    

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    else:
        name = request.form["name"]
        password = request.form["password"]
        password2 = request.form["password2"]
        if password == password2:
            exist = db.execute("SELECT * FROM tbl_user WHERE name = ?", name)
            if exist:
                return redirect("/register")
            else:
                db.execute("INSERT INTO tbl_user (name, password, groupchats) VALUES (?,?,?)", name, password, "blank")
                return redirect("/login")
        else:
            return redirect("/register")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/groupchat", methods=["GET", "POST"])
def groupchat():
    if session.get("userid") is None:
        return redirect("/login")
    else:
        if request.method == "GET":
            return render_template("creategc.html")
        else:
            inviteid = request.form["inviteid"]
            _groupchat = db.execute("SELECT * FROM tbl_groupchats WHERE inviteid = ?", inviteid)
            if not _groupchat:
                #display error message
                return redirect("/groupechat")
            else:
               
                current_members = _groupchat[0]["members"]
                current_members += "," + str(session.get("userid"))
                db.execute("UPDATE tbl_groupchats SET members = ? WHERE id = ?", current_members, _groupchat[0]["id"])
                #you have joined message
                db.execute(f"INSERT INTO tbl_{_groupchat[0]['name']} (userid) VALUES ({session.get('userid')})")
                groupchats_ = db.execute(f"SELECT groupchats FROM tbl_user WHERE userid = ?", (session.get('userid'),))
                groupchats_ = groupchats_[0]["groupchats"]

                if groupchats_ == "blank":
                    groupchat = _groupchat[0]['name']
                else:
                    groupchat = groupchats_ + "," + _groupchat[0]['name']


                db.execute("UPDATE tbl_user SET groupchats = ? WHERE userid = ?", groupchat, session.get('userid'))
                print(_groupchat)
                return redirect(f"/profile/{_groupchat[0]['inviteid']}")


@app.route("/creategc", methods=["GET", "POST"])
def creategc():
    if session.get("userid") is None:
        return redirect("/login")
    else:
        if request.method == "GET":
            return render_template("creategc.html")
        else:
            name = request.form["name"]
            invite_id = str(uuid.uuid1())
            db.execute("INSERT INTO tbl_groupchats (name, inviteid, members) VALUES (?, ?, ?)", name, invite_id, str(session.get("userid")))

            create_table_sql = f"""
            CREATE TABLE "{"tbl_" + name}" (
            "id"	INTEGER NOT NULL,
            "name"	TEXT,
            "foodinterest"	TEXT,
            "activityinterest" TEXT,
            "budget" INTEGER,
            "profile_done" TEXT,
            "userid" INTEGER NOT NULL,
            PRIMARY KEY("id")
        );
            """

            db.execute(create_table_sql)
            db.execute(f"INSERT INTO tbl_{name} (userid) VALUES ({session.get('userid')})")
            groupchats_ = db.execute(f"SELECT groupchats FROM tbl_user WHERE userid = ?", (session.get('userid'),))
            groupchats_ = groupchats_[0]["groupchats"]

            if groupchats_ == "blank":
                groupchat = name
            else:
                groupchat = groupchats_ + "," + name


            print(groupchat)
            db.execute("UPDATE tbl_user SET groupchats = ? WHERE userid = ?", groupchat, session.get('userid'))
            return render_template("sharelink.html", trip_id = invite_id)


@app.route("/profile/<inviteid>", methods=["GET", "POST"])
def profile(inviteid):
    if session.get("userid") is None:
        return redirect("/login")
    else:
        if request.method == "GET":
            gc_name = db.execute("SELECT name FROM tbl_groupchats WHERE inviteid = ?", (inviteid))
            print(gc_name)
            return render_template("profile.html", gc_name = gc_name[0]["name"], inviteid = inviteid)
        else:
            print("im in post")
            gc_name = db.execute("SELECT name FROM tbl_groupchats WHERE inviteid = ?", (inviteid))
            print(gc_name)

            name = request.form["name"]
            budget = request.form["budget"]
            int_activity = request.form["activitiesint"]
            int_restaurant = request.form["restaurantint"]

            print("i got inputs")

            db.execute(f"UPDATE tbl_{gc_name[0]['name']} SET name = ?, budget = ?, activityinterest = ?, foodinterest = ?, profile_done = ? WHERE userid = ?", name, int(budget), int_activity, int_restaurant, "True", session.get('userid'))

            print("sql worked")
            return redirect("/dashboard")
            

def GenerateFoodPlaces(name):
    interests = db.execute(f"SELECT foodinterest FROM tbl_{name}")
    food_places_string = ""
    for interest in interests:
        food_results = gmaps.places_nearby(location = "45.481227499999996,-73.611569", 
        radius = 50000, 
        open_now = False, 
        type = "",
        keyword=interest["foodinterest"]
        )

        for place in food_results['results']:
            my_place_id = place['place_id']
            my_fields = ["place_id", "name", "geometry"]
            place_details = gmaps.place(place_id = my_place_id, fields = my_fields)

            food_places_string += str(place_details)

    return food_places_string

def GenerateActivityPlaces(name):
    interests = db.execute(f"SELECT activityinterest FROM tbl_{name}")
    activity_places_string = ""
    for interest in interests:
        activity_results = gmaps.places_nearby(location = "45.481227499999996,-73.611569", 
        radius = 50000, 
        open_now = False, 
        type = "",
        keyword=interest["activityinterest"]
        )

        for place in activity_results['results']:
            my_place_id = place['place_id']
            my_fields = ["place_id", "name", "geometry"]
            place_details = gmaps.place(place_id = my_place_id, fields = my_fields)

            activity_places_string += str(place_details)

    return activity_places_string

def GenerateEvents(food, activity):
    while True:
        response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "you are making a group event in JSON {'name': 'Day 1', 'time': [{'breakfast': 'Boom J's Cuisine', 'activity':'Bowling', 'lunch': 'Korean BBQ', 'activity2': skating montreal, 'dinner': 'Boom J's Cuisine'}], 'latitude': 45.45630620000001, 'longitude': -73.5950002} Day 1,  {'latitude:' value, 'longitude': value 'name': 'Day 2', 'time': ('Oriental Fusion', 'Playground', 'Cafe Asia Plus', 'Triple 7 Casino', 'DonDonYa')}]. You do not talk, just send the python list like the example. No events = [] just []."},
            {"role": "user", "content": f"Here's food places {food} and activities places {activity}. Create 5 days of events with each breakfast, activity, lunch, activity dinner schedule. Also add latitude and longitude. Return as a JSON"}
        ]
    )

        response = response.choices[0].message.content
        try:
            return json.loads(response)
        except:
            print("try again") 

    return json.loads(response)
        


def GetPlaceInfo(place):
    print("I was called")

    # Check the content of app.config["places"]
    print(app.config["places"])

    corrected_json = app.config["places"].replace("'", '"')
    corrected_json = corrected_json.replace("\n", "\\n").replace("\t", "\\t")

    # Assuming app.config["places"] is a JSON string representing a list
    try:
        all_data = json.loads(corrected_json)
    except json.JSONDecodeError as e:
        print("Error parsing corrected JSON:", e)
        return

    # Iterate over the parsed list
    for data in all_data:
        print(data)
    

if __name__ == '__main__':
    app.run(debug=True)
