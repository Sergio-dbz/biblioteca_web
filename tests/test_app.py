from app import app


def test_login_page_loads():
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/login")

    assert response.status_code == 200
    assert b'name="email"' in response.data
    assert b'name="senha"' in response.data
