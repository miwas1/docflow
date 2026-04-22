from classifier_service.main import app


def test_health_endpoint_returns_classifier_contract() -> None:
    route = next(route for route in app.routes if route.path == "/healthz")

    assert route.methods == {"GET"}
    assert route.endpoint() == {"status": "ok", "service": "classifier"}


def test_classification_route_is_present_in_app_routes() -> None:
    route = next(route for route in app.routes if route.path == "/v1/classifications:run")

    assert route.methods == {"POST"}
