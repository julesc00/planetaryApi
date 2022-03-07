import os

from flask import Flask, jsonify, request

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float

from flask_marshmallow import Marshmallow

from flask_jwt_extended import JWTManager, jwt_required, create_access_token


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'planets.db')}"
app.config["JWT_SECRET_KEY"] = "super_secret"  # for learning purposes, not for production
jwt = JWTManager(app)

# Initialize db before I can start using it.
db = SQLAlchemy(app)
# Instantiate flask-marshmallow serialization tool
ma = Marshmallow(app)


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    firstname = Column(String)
    lastname = Column(String)
    email = Column(String, unique=True)
    password = Column(String)

    def __repr__(self):
        return "<User %r>" % self.firstname.title()


class Planet(db.Model):
    __tablename__ = "planets"
    planet_id = Column(Integer, primary_key=True)
    planet_name = Column(String)
    planet_type = Column(String)
    home_star = Column(String)
    mass = Column(Float)
    radius = Column(Float)
    distance = Column(Float)


class UserSchema(ma.Schema):
    """User object serializer."""
    class Meta:
        fields = ("id", "firstname", "lastname", "email", "password")


class PlanetSchema(ma.Schema):
    """Planet object serializer."""
    class Meta:
        fields = ("planet_id", "planet_name", "planet_type", "home_star", "mass", "radius", "distance")


user_schema = UserSchema()
users_schema = UserSchema(many=True)
planet_schema = PlanetSchema()
planets_schema = PlanetSchema(many=True)


# DB scripts
# Create the database
@app.cli.command("db_create")
def db_create():
    db.create_all()
    print("Database created!")


# Destroy the database
@app.cli.command("db_drop")
def db_drop():
    db.drop_all()
    print("Database dropped")


# Seed database (test data)
@app.cli.command("db_seed")
def db_seed():
    mercury = Planet(
        planet_name="Mercury",
        planet_type="Class D",
        home_star="Sol",
        mass=3.258e23,
        radius=1516,
        distance=35.98e6
    )
    venus = Planet(
        planet_name="Venus",
        planet_type="Class K",
        home_star="Sol",
        mass=4.867e24,
        radius=3760,
        distance=67.24e6
    )
    earth = Planet(
        planet_name="Earth",
        planet_type="Class M",
        home_star="Sol",
        mass=5.972e24,
        radius=3959,
        distance=92.96e6
    )
    db.session.add(mercury)
    db.session.add(venus)
    db.session.add(earth)

    test_user = User(
        firstname="Jemima",
        lastname="Briones",
        email="jemima_eloise@earth.com",
        password="chulis2022"
    )
    db.session.add(test_user)

    db.session.commit()
    print("Database seeded")


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


@app.route("/super_simple", methods=["GET"])
def super_simple():
    return jsonify(message="hello Earth!")


@app.route("/parameters/", methods=["GET"])
def parameters():
    name = request.args.get("name")
    age = int(request.args.get("age"))

    if age < 18:
        return jsonify(message=f"Sorry {name.title()}, you aren't old enough, get lost."), 401
    else:
        return jsonify(message=f"Welcome back {name.title()}.")


@app.route("/url_variables/<string:name>/<int:age>/")
def url_variables(name: str, age: int):
    if age < 18:
        return jsonify(message=f"Sorry {name.title()}, you aren't old enough, get lost."), 401
    else:
        return jsonify(message=f"Welcome back {name.title()}.")


@app.route("/planets", methods=["GET"])
def list_planets():
    """List all planets"""
    planets = Planet.query.all()
    results = planets_schema.dump(planets)
    return jsonify(results)


@app.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    email = request.form["email"]
    test = User.query.filter_by(email=email).first()
    if test:
        return jsonify(message="Email already exists"), 409
    else:
        # This approach is if we're receiving the data from a html form, and not an api request.
        firstname = request.form["firstname"]
        lastname = request.form["lastname"]
        password = request.form["password"]
        user = User(
            firstname=firstname,
            lastname=lastname,
            email=email,
            password=password
        )
        db.session.add(user)
        db.session.commit()
        return jsonify(message="User created successfully"), 201


@app.route("/login", methods=["POST"])
def login():
    """Login a user."""
    if request.is_json:
        email = request.json["email"]
        password = request.json["password"]
    else:
        email = request.form["email"]
        password = request.form["password"]

    test = User.query.filter_by(email=email, password=password).first()
    if test:
        access_token = create_access_token(identity=email)
        return jsonify(message="Login succeeded", access_token=access_token)
    else:
        return jsonify(message="Bad email or password"), 401


# @app.route("/planets/", methods=["GET"])
# def planet_detail():
#     planet_id = request.args.get("planet_id")
#     planet = Planet.query.filter_by(planet_id=planet_id).first()
#     result = planet_schema.dump(planet)
#     print(result)
#     return jsonify(result)


if __name__ == '__main__':
    app.run()
