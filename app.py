import os

from flask import Flask, jsonify, request

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float

from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from flask_mail import Mail, Message


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'planets.db')}"
app.config["JWT_SECRET_KEY"] = "super_secret"  # for learning purposes, not for production

# Initialize the JWT manager
jwt = JWTManager(app)

# Mail testing password resetting feature with mailtrap.io
app.config['MAIL_SERVER'] = os.environ.get("MAIL_SERVER")
app.config['MAIL_PORT'] = 2525
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

# Initialize mail object.
mail = Mail(app)
mail.connect()
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


@app.route("/retrieve_password/<string:email>", methods=["GET"])
def retrieve_password(email: str):
    user = User.query.filter_by(email=email).first()
    if user:
        msg = Message(
            f"Your planetary API password is '{user.password}'",
            sender="admin@planetary-api.com",
            recipients=[email]
        )
        mail.send(msg)
        return jsonify(message=f"Password sent to {email}")
    else:
        return jsonify(message="That email doesn't exists."), 401


@app.route("/planet_detail/<int:planet_id>", methods=["GET"])
def planet_details(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        result = planet_schema.dump(planet)
        print(planet)
        return jsonify(result)
    else:
        return jsonify(message="Such planet does not exists"), 404


@app.route("/add_planet", methods=["POST"])
@jwt_required()
def add_planet():
    planet_name = request.form["planet_name"].title()
    planet_type = request.form["planet_type"]
    home_star = request.form["home_star"]
    mass = float(request.form["mass"])
    radius = float(request.form["radius"])
    distance = float(request.form["distance"])

    test_planet = Planet.query.filter_by(planet_name=planet_name).first()
    if test_planet:
        return jsonify("Theres is already a planet with that name."), 409
    else:
        new_planet = Planet(
            planet_name=planet_name,
            planet_type=planet_type,
            home_star=home_star,
            mass=mass,
            radius=radius,
            distance=distance
        )

        db.session.add(new_planet)
        db.session.commit()
        return jsonify(message=f"{planet_name} was added successfully."), 201


@app.route("/update_planet", methods=["PUT"])
@jwt_required()
def update_planet():
    planet_id = int(request.form["planet_id"])
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        planet.planet_name = request.form["planet_name"]
        planet.planet_type = request.form["planet_type"]
        planet.home_star = request.form["home_star"]
        planet.mass = float(request.form["mass"])
        planet.radius = float(request.form["radius"])
        planet.distance = float(request.form["distance"])

        # There is no special method to just update.
        db.session.commit()
        return jsonify(message=f"{planet.planet_name} was updated!"), 202
    else:
        return jsonify(message="That planet does not exists"), 404


@app.route("/remove_planet/<int:planet_id>", methods=["DELETE"])
@jwt_required()
def remove_planet(planet_id: int):
    planet = Planet.query.filter_by(planet_id=planet_id).first()
    if planet:
        db.session.delete(planet)
        db.session.commit()
        return jsonify(message="Planet was deleted."), 202
    else:
        return jsonify(message="There is no planet with that id.")


if __name__ == '__main__':
    app.run()
