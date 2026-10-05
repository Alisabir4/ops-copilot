from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.backend.database import Base
from app.backend.models import Product, Customer, Sale, Document, DocumentChunk, User
from app.backend.services import low_stock, sales_summary, compare_sales, revenue_trend, search_documents, route_request
from app.backend.auth import hash_password, verify_password

def setup_db():
    engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return Session(engine)

def test_low_stock_uses_inclusive_reorder_boundary():
    db=setup_db();db.add_all([Product(sku="a",name="A",category="Office",price=10,cost=4,stock=5,reorder_level=5),Product(sku="b",name="B",category="Office",price=10,cost=4,stock=6,reorder_level=5)]);db.commit()
    assert [p.name for p in low_stock(db)]==["A"]

def test_sales_summary_aggregates_real_rows_and_bounds_days():
    db=setup_db();c=Customer(name="Test Customer",email="test@example.com");db.add(c);db.flush();now=datetime.now(timezone.utc)
    db.add_all([Sale(customer_id=c.id,product_id=1,quantity=2,unit_price=12.5,sold_at=now),Sale(customer_id=c.id,product_id=1,quantity=1,unit_price=10,sold_at=now-timedelta(days=400))]);db.commit()
    result=sales_summary(db,30)
    assert result["revenue"]==25 and result["orders"]==1 and result["average_order_value"]==25
    assert sales_summary(db,0)["orders"]==1

def test_sales_comparison_compares_adjacent_periods():
    db=setup_db();c=Customer(name="Compare Customer",email="compare@example.com");db.add(c);db.flush();now=datetime.now(timezone.utc)
    db.add_all([Sale(customer_id=c.id,product_id=1,quantity=1,unit_price=100,sold_at=now-timedelta(days=4)),Sale(customer_id=c.id,product_id=1,quantity=1,unit_price=50,sold_at=now-timedelta(days=35))]);db.commit()
    result=compare_sales(db,30)
    assert result["current_revenue"]==100 and result["previous_revenue"]==50 and result["change_percent"]==100.0

def test_revenue_trend_returns_daily_sold_at_and_revenue_rows():
    db=setup_db();c=Customer(name="Trend Customer",email="trend@example.com");db.add(c);db.flush();now=datetime.now(timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0)
    db.add_all([
        Sale(customer_id=c.id,product_id=1,quantity=2,unit_price=10,sold_at=now),
        Sale(customer_id=c.id,product_id=1,quantity=1,unit_price=5,sold_at=now-timedelta(hours=3)),
        Sale(customer_id=c.id,product_id=1,quantity=1,unit_price=7,sold_at=now-timedelta(days=1)),
    ]);db.commit()
    rows=revenue_trend(db,90)
    assert rows[-1]=={"sold_at":now.date().isoformat(),"revenue":25.0}
    assert rows[0]=={"sold_at":(now-timedelta(days=1)).date().isoformat(),"revenue":7.0}
    assert all(set(row)=={"sold_at","revenue"} for row in rows)

def test_document_retrieval_returns_cited_file_metadata(monkeypatch):
    # Keep unit tests offline even on machines where the optional embedding
    # package is present but its model weights have not been cached.
    import app.backend.services as services
    def unavailable_embedding(_texts):
        raise RuntimeError("Embedding model not available in unit test")
    monkeypatch.setattr(services, "_embed", unavailable_embedding)
    db=setup_db();user=User(email="a@b.test",name="Test",password_hash="hash",role="admin");db.add(user);db.flush();doc=Document(filename="returns.md",content_type="text/markdown",uploaded_by=user.id,chunk_count=1);db.add(doc);db.flush();db.add(DocumentChunk(document_id=doc.id,page=2,content="Refunds are available within thirty days."));db.commit()
    hit=search_documents(db,"refunds thirty days")[0]
    assert hit["filename"]=="returns.md" and hit["page"]==2

def test_tool_router_creates_a_reorder_proposal_payload_without_execution():
    db=setup_db();db.add(Product(sku="low",name="Low Item",category="Office",price=10,cost=5,stock=1,reorder_level=8));db.commit()
    result=route_request(db,"Prepare reorder request for low stock")
    assert result["kind"]=="action" and result["data"][0]["suggested_quantity"]==15
    assert "get_low_stock_products" in result["tools"]

def test_passwords_are_hashed_and_verified():
    hashed=hash_password("correct-horse-battery")
    assert hashed!="correct-horse-battery" and verify_password("correct-horse-battery",hashed)
    assert not verify_password("wrong-password",hashed)
