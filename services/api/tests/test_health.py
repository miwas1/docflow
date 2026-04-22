from api_service.main import app


def test_health_endpoint_returns_api_contract() -> None:
    route = next(route for route in app.routes if route.path == "/healthz")

    assert route.methods == {"GET"}
    assert route.endpoint() == {"status": "ok", "service": "api"}
