from resonance.server.routes.device import device_bp
from resonance.server.routes.config import config_bp
from resonance.server.routes.scheduler import scheduler_bp
from resonance.server.routes.status import status_bp
from resonance.server.routes.business import business_bp
from resonance.server.routes.debug import debug_bp


def register_blueprints(app):
    app.register_blueprint(device_bp, url_prefix="/api/device")
    app.register_blueprint(config_bp, url_prefix="/api/config")
    app.register_blueprint(scheduler_bp, url_prefix="/api/scheduler")
    app.register_blueprint(status_bp, url_prefix="/api/status")
    app.register_blueprint(business_bp, url_prefix="/api/business")
    app.register_blueprint(debug_bp, url_prefix="/api/debug")
