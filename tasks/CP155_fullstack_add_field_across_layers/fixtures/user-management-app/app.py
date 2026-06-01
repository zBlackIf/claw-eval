"""Flask application — user management REST API + web UI."""
from flask import Flask, jsonify, render_template, request

from models import db
from schemas import UserCreateSchema, UserUpdateSchema, UserResponseSchema
from services import UserService


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = "static/uploads"

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # --- REST API routes ---

    @app.route("/api/users", methods=["GET"])
    def api_list_users():
        users = UserService.list_users()
        return jsonify([UserResponseSchema.from_orm(u).dict() for u in users])

    @app.route("/api/users/<int:user_id>", methods=["GET"])
    def api_get_user(user_id):
        user = UserService.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(UserResponseSchema.from_orm(user).dict())

    @app.route("/api/users", methods=["POST"])
    def api_create_user():
        data = UserCreateSchema(**request.json)
        user = UserService.create_user(data)
        return jsonify(UserResponseSchema.from_orm(user).dict()), 201

    @app.route("/api/users/<int:user_id>", methods=["PUT"])
    def api_update_user(user_id):
        data = UserUpdateSchema(**request.json)
        user = UserService.update_user(user_id, data)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(UserResponseSchema.from_orm(user).dict())

    @app.route("/api/users/<int:user_id>", methods=["DELETE"])
    def api_delete_user(user_id):
        success = UserService.delete_user(user_id)
        if not success:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"message": "User deactivated"})

    # --- Web UI routes ---

    @app.route("/")
    def index():
        users = UserService.list_users()
        return render_template("index.html", users=users)

    @app.route("/users/new", methods=["GET"])
    def new_user_form():
        return render_template("user_form.html", user=None)

    @app.route("/users/<int:user_id>/edit", methods=["GET"])
    def edit_user_form(user_id):
        user = UserService.get_user(user_id)
        if not user:
            return "User not found", 404
        return render_template("user_form.html", user=user)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
