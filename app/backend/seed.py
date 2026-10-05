"""Create the repeatable Northstar Outfitters portfolio dataset.

Run from the repository root with ``python -m app.backend.seed``. Each run
rebuilds the demo business records and their dependent history from a fixed
fixture while preserving user accounts and documents uploaded by a user.
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.backend.auth import hash_password, verify_password
from app.backend.database import Base, SessionLocal, engine
from app.backend.models import (
    AgentRun, AgentToolCall, Approval, AuditLog, AutomationLog, Conversation,
    Customer, Document, DocumentChunk, Message, Order, OrderItem, Product,
    Role, Sale, User,
)
from app.backend.services import low_stock, sales_summary, top_products

DEMO_ACCOUNTS = (
    ("admin@demo.local", "Demo Admin", "admin", "DemoAdmin123!"),
    ("manager@demo.local", "Morgan Manager", "manager", "DemoManager123!"),
    ("employee@demo.local", "Evan Employee", "employee", "DemoEmployee123!"),
)

# sku, name, category, price, unit cost, ending stock, reorder point, sales weight
PRODUCTS = (
    ("NSO-1001", "Cascadia Trail Pack 28L", "Packs & Travel", 124.00, 61.00, 34, 12, 9),
    ("NSO-1002", "Rainier Daypack 18L", "Packs & Travel", 86.00, 39.00, 7, 12, 8),
    ("NSO-1003", "Coastal Weekender Duffel", "Packs & Travel", 148.00, 74.00, 23, 8, 5),
    ("NSO-1004", "Alpine Packing Cube Set", "Packs & Travel", 38.00, 15.50, 52, 15, 6),
    ("NSO-1005", "Ridgeline Merino Crew", "Apparel", 78.00, 31.00, 5, 14, 8),
    ("NSO-1006", "Switchback Fleece Jacket", "Apparel", 132.00, 58.00, 29, 10, 7),
    ("NSO-1007", "North Coast Rain Shell", "Apparel", 168.00, 79.00, 16, 8, 6),
    ("NSO-1008", "Trailhead Merino Socks, 3-Pack", "Apparel", 32.00, 11.00, 63, 20, 10),
    ("NSO-1009", "High Desert Sun Hat", "Apparel", 42.00, 16.00, 41, 12, 5),
    ("NSO-1010", "Evergreen Camp Blanket", "Camp & Home", 98.00, 43.00, 21, 8, 6),
    ("NSO-1011", "Glacier Vacuum Flask 750ml", "Camp & Home", 46.00, 18.50, 0, 16, 10),
    ("NSO-1012", "Juniper Enamel Cook Set", "Camp & Home", 112.00, 49.00, 18, 8, 4),
    ("NSO-1013", "Lookout Headlamp 450", "Camp & Home", 54.00, 21.00, 9, 12, 7),
    ("NSO-1014", "Ponderosa Pour-Over Kit", "Camp & Home", 64.00, 26.00, 38, 10, 5),
    ("NSO-1015", "Alpine Trekking Poles", "Trail Equipment", 104.00, 46.00, 27, 8, 6),
    ("NSO-1016", "Granite Ridge Hiking Gaiters", "Trail Equipment", 58.00, 22.00, 32, 10, 4),
    ("NSO-1017", "Switchback Hydration Vest", "Trail Equipment", 118.00, 52.00, 4, 12, 8),
    ("NSO-1018", "Summit Carbon Trek Pole Pair", "Trail Equipment", 189.00, 92.00, 3, 6, 4),
    ("NSO-1019", "Wildflower Trail Journal", "Accessories", 24.00, 7.50, 48, 14, 5),
    ("NSO-1020", "Field Notes Map Case", "Accessories", 29.00, 9.00, 0, 12, 5),
    ("NSO-1021", "Cedar Ridge Leather Gloves", "Accessories", 72.00, 29.00, 20, 8, 4),
    ("NSO-1022", "Moraine Camp Mug Set", "Camp & Home", 36.00, 13.00, 46, 12, 7),
    ("NSO-1023", "Northstar Repair & Care Kit", "Accessories", 26.00, 8.00, 72, 18, 4),
    ("NSO-1024", "Timberline Merino Beanie", "Apparel", 48.00, 18.00, 2, 10, 6),
    ("NSO-1025", "Cascade Solar Lantern", "Camp & Home", 84.00, 35.00, 31, 10, 5),
    ("NSO-1026", "Basecamp First Aid Roll", "Trail Equipment", 44.00, 17.00, 24, 10, 6),
    ("NSO-1027", "Three Sisters Picnic Tote", "Packs & Travel", 68.00, 27.00, 17, 8, 5),
    ("NSO-1028", "Canyon Insulated Lunch Flask", "Camp & Home", 52.00, 20.00, 39, 12, 7),
    ("NSO-1029", "Old Growth Canvas Apron", "Accessories", 62.00, 23.00, 4, 8, 3),
    ("NSO-1030", "Trail Marker Reflective Band", "Trail Equipment", 18.00, 5.00, 57, 18, 5),
    ("NSO-1031", "Northstar Merino Base Layer", "Apparel", 108.00, 44.00, 26, 10, 7),
    ("NSO-1032", "Coast Range Travel Organizer", "Packs & Travel", 34.00, 12.00, 43, 14, 4),
    ("NSO-1033", "Larchwood Camp Chair", "Camp & Home", 138.00, 63.00, 12, 6, 4),
    ("NSO-1034", "Timberline Trail Gaiter Pro", "Trail Equipment", 76.00, 31.00, 6, 8, 3),
)

# name, email, segment. Addresses use the reserved .example domain.
CUSTOMERS = (
    ("Maya Chen", "maya.chen@northstar.example", "VIP"),
    ("Ethan Brooks", "ethan.brooks@northstar.example", "VIP"),
    ("Sofia Patel", "sofia.patel@northstar.example", "VIP"),
    ("Lucas Bennett", "lucas.bennett@northstar.example", "VIP"),
    ("Amara Johnson", "amara.johnson@northstar.example", "VIP"),
    ("Noah Kim", "noah.kim@northstar.example", "VIP"),
    ("Isabel Rivera", "isabel.rivera@northstar.example", "VIP"),
    ("Oliver Grant", "oliver.grant@northstar.example", "VIP"),
    ("Priya Nair", "priya.nair@northstar.example", "Repeat"),
    ("Jack Sullivan", "jack.sullivan@northstar.example", "Repeat"),
    ("Leila Hassan", "leila.hassan@northstar.example", "Repeat"),
    ("Mateo Alvarez", "mateo.alvarez@northstar.example", "Repeat"),
    ("Grace Park", "grace.park@northstar.example", "Repeat"),
    ("Aiden Foster", "aiden.foster@northstar.example", "Repeat"),
    ("Zara Mahmood", "zara.mahmood@northstar.example", "Repeat"),
    ("Theo Martin", "theo.martin@northstar.example", "Repeat"),
    ("Nina Wallace", "nina.wallace@northstar.example", "Repeat"),
    ("Caleb Wright", "caleb.wright@northstar.example", "Repeat"),
    ("Hana Suzuki", "hana.suzuki@northstar.example", "Repeat"),
    ("Julian Reyes", "julian.reyes@northstar.example", "Repeat"),
    ("Ava Thompson", "ava.thompson@northstar.example", "Repeat"),
    ("Omar Farouk", "omar.farouk@northstar.example", "Repeat"),
    ("Elena Petrova", "elena.petrova@northstar.example", "Repeat"),
    ("Miles Cooper", "miles.cooper@northstar.example", "Repeat"),
    ("Rina Das", "rina.das@northstar.example", "Repeat"),
    ("Samuel Ortiz", "samuel.ortiz@northstar.example", "Repeat"),
    ("Chloe Williams", "chloe.williams@northstar.example", "Repeat"),
    ("Arjun Mehta", "arjun.mehta@northstar.example", "Repeat"),
    ("Lily Anderson", "lily.anderson@northstar.example", "Repeat"),
    ("Benjamin Cole", "benjamin.cole@northstar.example", "Repeat"),
    ("Layla Haddad", "layla.haddad@northstar.example", "Standard"),
    ("Henry Walsh", "henry.walsh@northstar.example", "Standard"),
    ("Fatima Ali", "fatima.ali@northstar.example", "Standard"),
    ("Gabriel Silva", "gabriel.silva@northstar.example", "Standard"),
    ("Mei Lin", "mei.lin@northstar.example", "Standard"),
    ("Dylan Price", "dylan.price@northstar.example", "Standard"),
    ("Aisha Rahman", "aisha.rahman@northstar.example", "Standard"),
    ("Finn O'Connell", "finn.oconnell@northstar.example", "Standard"),
    ("Clara Jensen", "clara.jensen@northstar.example", "Standard"),
    ("Rafael Costa", "rafael.costa@northstar.example", "Standard"),
    ("Sienna Moore", "sienna.moore@northstar.example", "Standard"),
    ("Dev Shah", "dev.shah@northstar.example", "Standard"),
)

DEMO_DOCUMENTS = {
    "Northstar Returns and Exchanges.md": (
        "text/markdown",
        ((1, "Northstar Outfitters | Returns and Exchanges | Customer Operations | Revised 15 August 2026\n\nCustomers may request a return within 30 calendar days after delivery. Items must be unused, clean, and in their original packaging with proof of purchase. To begin, contact care@northstar.example with the order number and reason for return. Gift purchases may be returned for store credit. Personalized items, clearance items marked final sale, and used technical safety equipment are not eligible for return.\n\nOnce an eligible return reaches our warehouse, the team inspects it within three business days. Approved refunds go to the original payment method and typically appear within five to seven business days. Northstar covers return shipping for damaged or incorrectly shipped items; other returns use a customer-provided label."),
         (2, "Exchanges are subject to available inventory. Customer Care can hold a replacement item for five business days while the original item is in transit. A price difference is charged or refunded to the original payment method. Orders damaged in transit should be reported within seven days of delivery with photographs of the item and packaging.")),
    ),
    "Northstar Inventory Replenishment Playbook.md": (
        "text/markdown",
        ((1, "Northstar Outfitters | Inventory Replenishment Playbook | Supply Operations | Revised 2 September 2026\n\nThe inventory reorder point on each product record is the trigger for replenishment review. The buyer reviews items at or below that threshold every Monday and Thursday. An item is considered critical when its available stock is at or below half of the reorder point; zero available units require same-day review.\n\nA proposed purchase quantity should restore approximately two reorder cycles of coverage, less stock currently on hand. Check the open purchase schedule and supplier lead time before placing any purchase order. Typical inbound lead time is 10 to 15 business days for domestic partners and 25 to 35 business days for overseas partners."),
         (2, "Approval controls: Employees may prepare a reorder proposal but may not contact a supplier or commit company funds. A manager or administrator must verify the product, quantity, supplier availability, and estimated spend. Only an approved request may be sent to the purchasing workflow. Record the approver, decision date, supplier confirmation, and expected delivery date.\n\nFor a stockout or a projected stockout before the next delivery, notify the Operations Manager and prioritize the request for review. Do not substitute a product or exceed the proposed quantity without renewed approval.")),
    ),
    "Northstar Customer Care Standards.md": (
        "text/markdown",
        ((1, "Northstar Outfitters | Customer Care Standards | Customer Experience | Revised 20 July 2026\n\nOur service promise is practical advice, durable gear, and straightforward support. Acknowledge customer inquiries within one business day. For product fit or trail-use questions, confirm the customer's intended activity and conditions before recommending equipment. Never promise a delivery date until it is confirmed by the carrier.\n\nCustomer segments in the operations workspace are based on purchase history: VIP identifies consistently high-value repeat customers, Repeat identifies customers with multiple purchases, and Standard identifies customers with one or no recorded purchases. These labels support service context and do not replace individual customer preferences or consent."),),
    ),
}

LEGACY_SKUS = tuple(f"SKU-{number}" for number in range(1000, 1032))
LEGACY_CUSTOMER_EMAILS = tuple(f"customer{number}@example.com" for number in range(1, 41))
SEED = 20261005


def _ensure_roles(db: Session) -> None:
    descriptions = {
        "admin": "Full workspace access",
        "manager": "Business operations and approvals",
        "employee": "Read operations data and own requests",
    }
    for name, description in descriptions.items():
        role = db.query(Role).filter_by(name=name).first()
        if role is None:
            db.add(Role(name=name, description=description))
        else:
            role.description = description


def _ensure_demo_users(db: Session) -> None:
    for email, name, role, password in DEMO_ACCOUNTS:
        user = db.query(User).filter_by(email=email).first()
        if user is None:
            db.add(User(email=email, name=name, role=role, password_hash=hash_password(password)))
            continue
        user.name, user.role, user.active = name, role, True
        try:
            valid = verify_password(password, user.password_hash)
        except (ValueError, TypeError):
            valid = False
        if not valid:
            user.password_hash = hash_password(password)


def _clear_previous_dataset(db: Session) -> None:
    """Remove workspace demo business records before rebuilding the fixture."""
    db.query(Message).delete(synchronize_session=False)
    db.query(Conversation).delete(synchronize_session=False)
    db.query(AgentToolCall).delete(synchronize_session=False)
    db.query(AgentRun).delete(synchronize_session=False)
    db.query(AutomationLog).delete(synchronize_session=False)
    db.query(Approval).delete(synchronize_session=False)
    db.query(AuditLog).delete(synchronize_session=False)
    db.query(OrderItem).delete(synchronize_session=False)
    db.query(Order).delete(synchronize_session=False)
    db.query(Sale).delete(synchronize_session=False)

    # Remove old generic seed rows as well as the current canonical catalog.
    db.query(Product).filter(
        (Product.sku.like("NSO-%")) | (Product.sku.in_(LEGACY_SKUS))
    ).delete(synchronize_session=False)
    db.query(Customer).filter(
        (Customer.email.like("%@northstar.example")) | (Customer.email.in_(LEGACY_CUSTOMER_EMAILS))
    ).delete(synchronize_session=False)

    old_names = list(DEMO_DOCUMENTS) + ["Company Policies.md"]
    documents = db.query(Document).filter(Document.filename.in_(old_names)).all()
    for document in documents:
        db.query(DocumentChunk).filter_by(document_id=document.id).delete(synchronize_session=False)
        db.delete(document)
    db.flush()


def _create_catalog(db: Session) -> tuple[list[Product], list[Customer]]:
    products = [Product(sku=sku, name=name, category=category, price=price, cost=cost,
                        stock=stock, reorder_level=reorder)
                for sku, name, category, price, cost, stock, reorder, _ in PRODUCTS]
    customers = [Customer(name=name, email=email, segment=segment)
                 for name, email, segment in CUSTOMERS]
    db.add_all(products + customers)
    db.flush()
    return products, customers


def _sales_plan() -> list[tuple[int, int, int, datetime]]:
    """Return deterministic, seasonal transactions spanning six months."""
    rng = random.Random(SEED)
    entries = []
    # The latest month has fewer orders than the preceding month, creating a
    # genuine data-derived cooling trend without embedding a chart value.
    windows = ((90, 0, 29), (110, 30, 59), (100, 60, 179))
    product_weights = [row[7] for row in PRODUCTS]
    for count, min_day, max_day in windows:
        for index in range(count):
            product_index = rng.choices(range(len(PRODUCTS)), weights=product_weights, k=1)[0]
            if min_day == 0:
                customer_index = rng.randrange(0, 30)
            elif min_day == 30:
                customer_index = rng.randrange(0, 30)
            elif index < 8:
                customer_index = 30 + index
            else:
                # Eight customers have no activity in the latest 60 days; four
                # additional contacts have not purchased in the seeded period.
                customer_index = rng.randrange(0, 38)
            quantity = rng.choices((1, 2, 3, 4), weights=(58, 28, 11, 3), k=1)[0]
            # Recent baskets have a slightly lower value, alongside lower order
            # volume. All revenue is derived from catalog prices and quantities.
            if min_day == 0 and product_index in (2, 17, 32):
                quantity = 1
            day = rng.randint(min_day, max_day)
            sold_at = datetime.now(timezone.utc) - timedelta(
                days=day, hours=rng.randint(8, 20), minutes=rng.randint(0, 59)
            )
            entries.append((customer_index, product_index, quantity, sold_at))
    entries.sort(key=lambda entry: entry[3])
    return entries


def _create_sales_and_orders(db: Session, products: list[Product], customers: list[Customer]) -> None:
    for customer_index, product_index, quantity, sold_at in _sales_plan():
        customer, product = customers[customer_index], products[product_index]
        sale = Sale(customer_id=customer.id, product_id=product.id, quantity=quantity,
                    unit_price=product.price, sold_at=sold_at)
        order = Order(customer_id=customer.id, status="completed", created_at=sold_at)
        db.add_all((sale, order))
        db.flush()
        db.add(OrderItem(order_id=order.id, product_id=product.id,
                         quantity=quantity, unit_price=product.price))


def _create_documents(db: Session, admin: User) -> list[Document]:
    created = []
    for filename, (content_type, pages) in DEMO_DOCUMENTS.items():
        doc = Document(filename=filename, content_type=content_type, uploaded_by=admin.id,
                       status="processed", chunk_count=len(pages),
                       created_at=datetime.now(timezone.utc) - timedelta(days=11))
        db.add(doc)
        db.flush()
        for page, content in pages:
            db.add(DocumentChunk(document_id=doc.id, page=page, content=content))
        created.append(doc)
    db.flush()
    return created


def _create_approval_history(db: Session, admin: User, manager: User, employee: User,
                             products: list[Product], now: datetime) -> list[Approval]:
    by_sku = {product.sku: product for product in products}

    def payload_for(skus: tuple[str, ...]) -> str:
        rows = []
        for sku in skus:
            product = by_sku[sku]
            rows.append({
                "product_id": product.id, "product": product.name, "stock": product.stock,
                "reorder_level": product.reorder_level,
                "suggested_quantity": max(0, product.reorder_level * 2 - product.stock),
            })
        return json.dumps(rows)

    approvals = [
        Approval(requested_by=employee.id, action_type="reorder_request",
                 payload=payload_for(("NSO-1011", "NSO-1020", "NSO-1005")), status="pending",
                 decision_note="", created_at=now - timedelta(hours=3)),
        Approval(requested_by=manager.id, action_type="reorder_request",
                 payload=payload_for(("NSO-1002", "NSO-1017")), status="approved",
                 decided_by=admin.id, decision_note="Quantities and supplier lead time reviewed.",
                 created_at=now - timedelta(days=3), decided_at=now - timedelta(days=3) + timedelta(hours=2)),
        Approval(requested_by=employee.id, action_type="reorder_request",
                 payload=payload_for(("NSO-1024",)), status="rejected", decided_by=manager.id,
                 decision_note="Consolidate with the next apparel purchase cycle.",
                 created_at=now - timedelta(days=6), decided_at=now - timedelta(days=6) + timedelta(hours=4)),
    ]
    db.add_all(approvals)
    db.flush()
    db.add_all([
        AutomationLog(approval_id=approvals[1].id, event="reorder_request", status="simulated",
                      response_summary="Demo mode: approved replenishment proposal recorded; no supplier contacted.",
                      created_at=approvals[1].decided_at),
        AutomationLog(approval_id=approvals[2].id, event="reorder_request", status="not_sent",
                      response_summary="Rejected proposal was not sent to a workflow.",
                      created_at=approvals[2].decided_at),
    ])
    return approvals


def _create_agent_and_audit_history(db: Session, admin: User, manager: User,
                                    employee: User, documents: list[Document],
                                    approvals: list[Approval], now: datetime) -> None:
    stock = low_stock(db)
    summary = sales_summary(db, 30)
    tops = top_products(db)
    low_response = "At or below reorder threshold: " + ", ".join(
        f"{item.name} ({item.stock} on hand; threshold {item.reorder_level})" for item in stock
    )
    runs = [
        AgentRun(user_id=manager.id, request="Which products are below their reorder threshold?",
                 response=low_response, status="completed", created_at=now - timedelta(days=1, hours=2)),
        AgentRun(user_id=admin.id, request="Summarize our sales performance this month.",
                 response=f"Recorded revenue: ${summary['revenue']:,.2f} across {summary['orders']} orders. Leading product: {tops[0]['name'] if tops else 'No recorded sales'}.",
                 status="completed", created_at=now - timedelta(days=1)),
    ]
    db.add_all(runs)
    db.flush()
    db.add_all([
        AgentToolCall(run_id=runs[0].id, tool_name="get_low_stock_products", result_summary=low_response,
                     created_at=runs[0].created_at),
        AgentToolCall(run_id=runs[1].id, tool_name="get_sales_summary", result_summary=json.dumps(summary),
                     created_at=runs[1].created_at),
        AgentToolCall(run_id=runs[1].id, tool_name="get_top_products", result_summary=json.dumps(tops),
                     created_at=runs[1].created_at),
    ])

    events = [
        (admin, "login", "session", "Demo administrator signed in", 0),
        (admin, "document_upload", documents[0].filename, f"Indexed {documents[0].chunk_count} policy passages", 10),
        (manager, "rag_retrieval", documents[1].filename, "Retrieved replenishment approval and stock policy", 22),
        (manager, "agent_run", str(runs[0].id), "Inventory threshold review completed", 28),
        (employee, "approval_created", str(approvals[0].id), "Critical stock replenishment submitted for review", 3),
        (admin, "approval_decision", str(approvals[1].id), "Replenishment proposal approved; demo workflow simulated", 3 * 24),
        (manager, "approval_decision", str(approvals[2].id), "Replenishment proposal returned for next purchase cycle", 6 * 24),
        (admin, "automation_simulated", str(approvals[1].id), "No external supplier notification sent in demo mode", 3 * 24),
        (admin, "report_generated", "business", "Weekly operations report prepared from recorded sales and inventory", 4),
        (admin, "agent_run", str(runs[1].id), "Sales summary and top-product tools completed", 24),
    ]
    db.add_all([
        AuditLog(user_id=user.id, event=event, resource=resource, status="success", details=details,
                 created_at=now - timedelta(hours=hours))
        for user, event, resource, details, hours in events
    ])


def seed_database(session_factory: Callable[[], Session] = SessionLocal,
                  db_engine=engine) -> dict[str, int]:
    """Create tables and rebuild the linked, deterministic demo workspace."""
    Base.metadata.create_all(bind=db_engine)
    db = session_factory()
    try:
        _ensure_roles(db)
        _ensure_demo_users(db)
        db.flush()
        admin = db.query(User).filter_by(email="admin@demo.local").one()
        manager = db.query(User).filter_by(email="manager@demo.local").one()
        employee = db.query(User).filter_by(email="employee@demo.local").one()
        _clear_previous_dataset(db)
        products, customers = _create_catalog(db)
        _create_sales_and_orders(db, products, customers)
        documents = _create_documents(db, admin)
        now = datetime.now(timezone.utc)
        approvals = _create_approval_history(db, admin, manager, employee, products, now)
        _create_agent_and_audit_history(db, admin, manager, employee, documents, approvals, now)
        db.commit()
        return {
            "users": db.query(User).count(), "products": db.query(Product).count(),
            "customers": db.query(Customer).count(), "sales": db.query(Sale).count(),
            "orders": db.query(Order).count(), "order_items": db.query(OrderItem).count(),
            "documents": db.query(Document).count(), "document_chunks": db.query(DocumentChunk).count(),
            "approvals": db.query(Approval).count(), "agent_runs": db.query(AgentRun).count(),
            "audit_logs": db.query(AuditLog).count(),
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    counts = seed_database()
    print("Northstar Outfitters demo seed complete: " + ", ".join(
        f"{key}={value}" for key, value in counts.items()
    ))
    print("Admin login: admin@demo.local / DemoAdmin123!")


if __name__ == "__main__":
    main()
