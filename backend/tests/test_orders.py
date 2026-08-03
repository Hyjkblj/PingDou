"""订单模块测试"""
from fastapi.testclient import TestClient


def test_create_order(client: TestClient, auth_headers, seed_product):
    """测试创建订单"""
    # 先获取商品
    product_response = client.get("/api/v1/products/current")
    product_id = product_response.json()["data"]["id"]

    # 创建订单
    response = client.post(
        "/api/v1/orders",
        json={"productId": product_id, "channel": "WECHAT_PAY"},
        headers={**auth_headers, "Idempotency-Key": "test-order-001"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["status"] == "PENDING_PAYMENT"
    assert data["data"]["amountCents"] == 1290
    assert "payment" in data["data"]


def test_create_order_idempotent(client: TestClient, auth_headers, seed_product):
    """测试订单幂等性"""
    product_response = client.get("/api/v1/products/current")
    product_id = product_response.json()["data"]["id"]

    # 第一次创建
    response1 = client.post(
        "/api/v1/orders",
        json={"productId": product_id, "channel": "WECHAT_PAY"},
        headers={**auth_headers, "Idempotency-Key": "test-order-idempotent"},
    )

    # 第二次创建（相同幂等键）
    response2 = client.post(
        "/api/v1/orders",
        json={"productId": product_id, "channel": "WECHAT_PAY"},
        headers={**auth_headers, "Idempotency-Key": "test-order-idempotent"},
    )

    # 应返回相同的订单
    assert response1.json()["data"]["id"] == response2.json()["data"]["id"]


def test_get_order(client: TestClient, auth_headers, seed_product):
    """测试查询订单"""
    product_response = client.get("/api/v1/products/current")
    product_id = product_response.json()["data"]["id"]

    # 创建订单
    create_response = client.post(
        "/api/v1/orders",
        json={"productId": product_id, "channel": "WECHAT_PAY"},
        headers={**auth_headers, "Idempotency-Key": "test-order-get"},
    )
    order_id = create_response.json()["data"]["id"]

    # 查询订单
    response = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == order_id
