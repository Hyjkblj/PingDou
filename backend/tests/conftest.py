"""测试配置和 Fixtures"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.domain.models import Product
from app.main import app

# 使用 SQLite 内存数据库进行测试
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """创建测试数据库表"""
    Base.metadata.create_all(test_engine)
    yield
    Base.metadata.drop_all(test_engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """每个测试前清理表数据"""
    session = TestSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture
def db():
    """数据库会话 fixture"""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db):
    """测试客户端 fixture"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_product(db):
    """创建测试商品"""
    product = Product(
        name="AI 拼豆图纸制作兑换码",
        price_cents=1290,
        list_price_cents=1990,
        currency="CNY",
        source_asset_limit=1,
        ai_candidate_count=2,
        edit_window_hours=72,
        download_retention_days=30,
        code_validity_days=180,
        export_formats=["PNG", "PDF", "CSV"],
        refund_policy_version="2026-08-01",
        is_active=True,
    )
    db.add(product)
    db.commit()
    return product


@pytest.fixture
def auth_headers(client):
    """获取认证 headers"""
    # 发送验证码
    client.post("/api/v1/auth/sms/send", json={"phone": "13800000000", "scene": "LOGIN"})
    # 登录
    response = client.post(
        "/api/v1/auth/sms/login",
        json={"phone": "13800000000", "code": "123456"},
    )
    data = response.json()
    token = data["data"]["accessToken"]
    return {"Authorization": f"Bearer {token}"}
