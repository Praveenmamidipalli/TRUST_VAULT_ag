import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.models.enums import UserRole


def test_argon2_password_hashing():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_validation():
    data = {"sub": "42", "email": "test@example.com", "role": "OWNER"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded["sub"] == "42"
    assert decoded["email"] == "test@example.com"
    assert decoded["role"] == "OWNER"
    assert "exp" in decoded


def test_user_registration_success(client):
    payload = {
        "email": "alice@trustvault.io",
        "username": "alice",
        "full_name": "Alice Smith",
        "password": "Password123!",
        "role": "OWNER"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@trustvault.io"
    assert data["user"]["username"] == "alice"
    assert data["user"]["role"] == "OWNER"
    assert data["user"]["is_active"] is True


def test_disallow_self_registration_as_admin(client):
    payload = {
        "email": "hacker@trustvault.io",
        "username": "hacker",
        "full_name": "Eve Hacker",
        "password": "Password123!",
        "role": "ADMIN"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    # Must be downgraded to VIEWER
    assert data["user"]["role"] == "VIEWER"


def test_duplicate_registration_rejection(client):
    payload = {
        "email": "bob@trustvault.io",
        "username": "bob",
        "password": "Password123!"
    }
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


def test_login_success(client):
    reg_payload = {
        "email": "carol@trustvault.io",
        "username": "carol",
        "password": "Password123!",
        "role": "OWNER"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login with username
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "carol",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Login with email
    login_res_email = client.post("/api/v1/auth/login", json={
        "username_or_email": "carol@trustvault.io",
        "password": "Password123!"
    })
    assert login_res_email.status_code == 200
    assert "access_token" in login_res_email.json()


def test_login_invalid_credentials(client):
    response = client.post("/api/v1/auth/login", json={
        "username_or_email": "nonexistent",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "Incorrect username/email or password" in response.json()["detail"]


def test_inactive_user_login_and_access_rejected(client, db_session):
    user = User(
        email="inactive@trustvault.io",
        username="inactive_user",
        hashed_password=hash_password("Password123!"),
        role=UserRole.VIEWER,
        is_active=False
    )
    db_session.add(user)
    db_session.commit()

    # Attempt login
    login_res = client.post("/api/v1/auth/login", json={
        "username_or_email": "inactive@trustvault.io",
        "password": "Password123!"
    })
    assert login_res.status_code == 403
    assert "Account is deactivated" in login_res.json()["detail"]

    # Attempt to use a valid token for an inactive user
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 403
    assert "Account is deactivated" in me_res.json()["detail"]


def test_get_current_user_profile(client):
    reg_payload = {
        "email": "dave@trustvault.io",
        "username": "dave",
        "password": "Password123!"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["access_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["email"] == "dave@trustvault.io"
    assert profile["username"] == "dave"
