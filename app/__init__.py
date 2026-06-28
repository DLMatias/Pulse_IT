import os

from flask import Flask

from . import db
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE=os.path.join(app.instance_path, "it_dashboard.sqlite"),
        SEED_DATABASE=True,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(bp)

    with app.app_context():
        db.init_database()
        if app.config.get("SEED_DATABASE", True):
            db.seed_database()

    return app

