import pytest

async def test_create_and_get_todo(client):
    # need a user first
    user = await client.post("/users/", json={"name": "Bob", "email": "bob@example.com"})
    uid = user.json()["id"]
    todo_payload = {"title": "Buy milk", "owner_id": uid}
    res = await client.post("/todos/", json=todo_payload)
    assert res.status_code == 201
    todo_id = res.json()["id"]

    res = await client.get(f"/todos/{todo_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Buy milk"
