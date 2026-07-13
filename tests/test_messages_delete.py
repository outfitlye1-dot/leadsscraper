def test_delete_all_messages(client, auth_headers, db_session):
    from app.models.campaign import MessageType
    from app.models.message import Message
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add_all(
        [
            Message(
                user_id=user.id,
                message_type=MessageType.email,
                message_content='{"subject": "Hi"}',
            ),
            Message(
                user_id=user.id,
                message_type=MessageType.whatsapp,
                message_content="Hello there",
            ),
        ]
    )
    db_session.commit()

    response = client.delete("/api/messages", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["deleted"] == 2

    list_resp = client.get("/api/messages", headers=auth_headers)
    assert list_resp.json()["total"] == 0


def test_delete_filtered_messages(client, auth_headers, db_session):
    from app.models.campaign import MessageType
    from app.models.message import Message
    from app.repositories.user_repository import UserRepository

    user = UserRepository(db_session).get_by_email("test@example.com")
    db_session.add_all(
        [
            Message(
                user_id=user.id,
                message_type=MessageType.email,
                message_content="email one",
            ),
            Message(
                user_id=user.id,
                message_type=MessageType.whatsapp,
                message_content="whatsapp one",
            ),
        ]
    )
    db_session.commit()

    response = client.delete(
        "/api/messages",
        headers=auth_headers,
        params={"message_type": "email"},
    )
    assert response.status_code == 200
    assert response.json()["deleted"] == 1

    list_resp = client.get("/api/messages", headers=auth_headers)
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["message_type"] == "whatsapp"
