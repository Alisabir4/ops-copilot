from collections.abc import Iterator
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backend.auth import verify_password, token_for
from app.backend.database import Base, get_db
from app.backend.main import app
from app.backend.models import (
    Approval, AuditLog, AutomationLog, Customer, Document, DocumentChunk, Order,
    OrderItem, Product, Role, Sale, User,
)
from app.backend.seed import seed_database


@pytest.fixture
def seeded_database():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=test_engine)
    counts_first = seed_database(factory, test_engine)
    yield factory, test_engine, counts_first
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_seed_creates_admin_and_is_idempotent(seeded_database):
    factory, test_engine, first_counts = seeded_database
    second_counts = seed_database(factory, test_engine)
    with factory() as db:
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        assert admin.role == "admin"
        assert admin.active is True
        assert verify_password("DemoAdmin123!", admin.password_hash)
        assert db.query(Role).filter_by(name="admin").one()
    assert second_counts == first_counts
    assert first_counts["products"] >= 30
    assert first_counts["customers"] >= 30
    assert first_counts["sales"] >= 100
    assert first_counts["documents"] >= 1


def test_seed_repairs_existing_admin_password_and_role(seeded_database):
    factory, test_engine, _ = seeded_database
    with factory() as db:
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        admin.password_hash = "invalid-or-stale-hash"
        admin.role = "employee"
        admin.active = False
        db.commit()

    seed_database(factory, test_engine)

    with factory() as db:
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        assert admin.role == "admin"
        assert admin.active is True
        assert verify_password("DemoAdmin123!", admin.password_hash)


def test_seed_rebuilds_consistent_northstar_demo_dataset(seeded_database):
    factory, test_engine, first_counts = seeded_database
    assert seed_database(factory, test_engine) == first_counts
    with factory() as db:
        products = db.query(Product).all()
        customers = db.query(Customer).all()
        sales = db.query(Sale).all()
        orders = db.query(Order).all()
        items = db.query(OrderItem).all()
        assert len(products) == 34
        assert len(customers) == 42
        assert len(sales) == len(orders) == len(items) == 300
        assert all(p.sku.startswith("NSO-") and not p.name.lower().startswith("product ") for p in products)
        assert all("customer" not in c.name.lower() and c.email.endswith("@northstar.example") for c in customers)
        assert not any(c.email.endswith("@example.com") for c in customers)
        now = datetime.now(timezone.utc)
        latest_purchase = {}
        for sale in sales:
            sold_at = sale.sold_at.replace(tzinfo=timezone.utc) if sale.sold_at.tzinfo is None else sale.sold_at
            latest_purchase[sale.customer_id] = max(latest_purchase.get(sale.customer_id, sold_at), sold_at)
        assert sum(customer.id not in latest_purchase for customer in customers) == 4
        assert sum(now - latest_purchase[c.id] > timedelta(days=60)
                   for c in customers if c.id in latest_purchase) >= 8

        orders_by_id = {order.id: order for order in orders}
        sale_links = Counter((sale.customer_id, sale.product_id, sale.quantity,
                              sale.unit_price, sale.sold_at) for sale in sales)
        order_links = Counter((order_by_id.customer_id, item.product_id, item.quantity,
                               item.unit_price, order_by_id.created_at)
                              for item in items
                              for order_by_id in (orders_by_id[item.order_id],))
        assert sale_links == order_links

        low = [product for product in products if product.stock <= product.reorder_level]
        assert len(low) >= 8
        assert any(product.stock == 0 for product in products)
        assert db.query(Document).filter(Document.filename == "Northstar Returns and Exchanges.md").count() == 1
        assert db.query(Document).filter(Document.filename == "Northstar Inventory Replenishment Playbook.md").count() == 1
        assert db.query(DocumentChunk).count() >= 5
        assert db.query(Approval).filter_by(status="pending").count() == 1
        assert db.query(Approval).filter_by(status="approved").count() == 1
        assert db.query(Approval).filter_by(status="rejected").count() == 1
        assert db.query(AutomationLog).count() == 2
        assert db.query(AuditLog).count() >= 8


def test_demo_documents_retrieve_coherent_policy_content(seeded_database, monkeypatch):
    import app.backend.services as services
    monkeypatch.setattr(services, "_embed", lambda _texts: (_ for _ in ()).throw(RuntimeError("offline")))
    factory, _, _ = seeded_database
    with factory() as db:
        from app.backend.services import search_documents
        hits = search_documents(db, "return refund original packaging thirty days")
        assert hits
        assert hits[0]["filename"] == "Northstar Returns and Exchanges.md"
        assert {hit["filename"] for hit in hits} == {"Northstar Returns and Exchanges.md"}
        assert "30 calendar days" in hits[0]["content"]
        assert search_documents(db, "supplier approval reorder point")


def test_demo_login_returns_usable_admin_jwt(seeded_database):
    factory, _, _ = seeded_database

    def override_get_db() -> Iterator:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/auth/login",
                json={"email": "admin@demo.local", "password": "DemoAdmin123!"},
            )
            assert response.status_code == 200, response.text
            token = response.json()["access_token"]
            assert response.json()["token_type"] == "bearer"
            me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            assert me.json()["email"] == "admin@demo.local"
            assert me.json()["role"] == "admin"
            assert client.post(
                "/auth/login",
                json={"email": "admin@demo.local", "password": "wrong-password"},
            ).status_code == 401
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_sales_trend_api_returns_plot_ready_schema(seeded_database):
    factory, _, _ = seeded_database
    with factory() as db:
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        customer = db.query(Customer).first()
        product = db.query(Product).first()
        db.add(Sale(customer_id=customer.id, product_id=product.id, quantity=3,
                    unit_price=product.price, sold_at=datetime.now(timezone.utc)))
        db.commit()
        token = token_for(admin)

    def override_get_db() -> Iterator:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/sales/trend?days=90", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200, response.text
        rows = response.json()
        assert rows
        assert all(set(row) == {"sold_at", "revenue"} for row in rows)
        assert all(datetime.fromisoformat(row["sold_at"]) for row in rows)
        assert all(isinstance(row["revenue"], (int, float)) for row in rows)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_seeded_policy_rag_endpoint_returns_cited_grounded_answer(seeded_database, monkeypatch):
    import app.backend.services as services
    def unexpected_embedding(_texts):
        raise AssertionError("Lexical-only seeded chunks should not initialize embeddings")
    monkeypatch.setattr(services, "_embed", unexpected_embedding)
    factory, _, _ = seeded_database
    with factory() as db:
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        token = token_for(admin)

    def override_get_db() -> Iterator:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.post(
                "/rag/query",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "What is the return window and refund timing?"},
            )
        assert response.status_code == 200, response.text
        result = response.json()
        assert "30 calendar days" in result["answer"]
        assert "five to seven business days" in result["answer"]
        assert any(source["filename"] == "Northstar Returns and Exchanges.md"
                   for source in result["sources"])
    finally:
        app.dependency_overrides.pop(get_db, None)
