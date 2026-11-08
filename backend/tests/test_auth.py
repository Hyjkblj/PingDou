"""认证模块测试"""
from fastapi.testclient import TestClient


def test_send_sms(client: TestClient):
    """测试发送短信验证码"""
    response = client.post("/api/v1/auth/sms/send", json={"phone": "13800000000", "scene": "LOGIN"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["cooldownSeconds"] == 60


def test_sms_login(client: TestClient):
    """测试手机号登录"""
    # 先发送验证码
    client.post("/api/v1/auth/sms/send", json={"phone": "13800000000", "scene": "LOGIN"})

    # 登录
    response = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800000000", "code": "123456"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data["data"]
    assert "refreshToken" in data["data"]
    assert data["data"]["user"]["phoneMasked"] == "138****0000"


def test_sms_login_invalid_code(client: TestClient):
    """测试验证码错误"""
    client.post("/api/v1/auth/sms/send", json={"phone": "13800000000", "scene": "LOGIN"})
    response = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800000000", "code": "000000"},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "SMS_CODE_INVALID"


def test_users_me(client: TestClient, auth_headers):
    """测试获取当前用户"""
    response = client.get("/api/v1/auth/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["phoneMasked"] == "138****0000"


def test_users_me_unauthorized(client: TestClient):
    """测试未登录访问"""
    response = client.get("/api/v1/auth/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "AUTH_REQUIRED"
