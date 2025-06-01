import pytest

async def test_create_and_get_user(client):
    payload = {"name": "Alice", "email": "alice@example.com"}
    res = await client.post("/users/", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alice"
    uid = data["id"]

    # get
    res = await client.get(f"/users/{uid}")
    assert res.status_code == 200
    assert res.json()["email"] == "alice@example.com"
