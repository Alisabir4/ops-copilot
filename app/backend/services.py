import json, logging, re
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.backend.models import Product, Sale, Customer, Document, DocumentChunk, AuditLog

log = logging.getLogger(__name__)

def audit(db: Session, user_id: int | None, event: str, resource: str = "", details: str = "", status: str = "success"):
    db.add(AuditLog(user_id=user_id, event=event, resource=resource, details=details[:1500], status=status)); db.commit()

def low_stock(db: Session):
    return db.query(Product).filter(Product.stock <= Product.reorder_level).order_by(Product.stock).all()

def sales_summary(db: Session, days: int = 30):
    since = datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 3650)))
    rows = db.query(Sale).filter(Sale.sold_at >= since).all()
    return {"revenue": round(sum(x.quantity*x.unit_price for x in rows),2), "orders": len(rows), "units": sum(x.quantity for x in rows), "average_order_value": round(sum(x.quantity*x.unit_price for x in rows)/len(rows),2) if rows else 0, "days": days}

def revenue_trend(db: Session, days: int = 90):
    """Return real sales aggregated by UTC calendar day as sold_at/revenue rows."""
    days=max(1,min(days,3650))
    since=datetime.now(timezone.utc)-timedelta(days=days)
    transactions=db.query(Sale.sold_at,Sale.quantity,Sale.unit_price).filter(Sale.sold_at>=since).order_by(Sale.sold_at).all()
    totals={}
    for sold_at,quantity,unit_price in transactions:
        # SQLite returns naive datetimes for timezone-aware columns; stored values
        # are UTC, while PostgreSQL values retain timezone information.
        day=(sold_at.replace(tzinfo=timezone.utc) if sold_at.tzinfo is None else sold_at.astimezone(timezone.utc)).date()
        totals[day]=totals.get(day,0.0)+quantity*unit_price
    return [{"sold_at":day.isoformat(),"revenue":round(total,2)} for day,total in sorted(totals.items())]

def compare_sales(db: Session, days: int = 30):
    """Compare equal adjacent periods using transaction rows, without inferring causes."""
    end=datetime.now(timezone.utc);start=end-timedelta(days=days);previous_start=start-timedelta(days=days)
    rows=db.query(Sale).filter(Sale.sold_at>=previous_start,Sale.sold_at<end).all()
    current=sum(s.quantity*s.unit_price for s in rows if (s.sold_at.replace(tzinfo=timezone.utc) if s.sold_at.tzinfo is None else s.sold_at)>=start)
    previous=sum(s.quantity*s.unit_price for s in rows if (s.sold_at.replace(tzinfo=timezone.utc) if s.sold_at.tzinfo is None else s.sold_at)<start)
    change=((current-previous)/previous*100) if previous else None
    return {"current_revenue":round(current,2),"previous_revenue":round(previous,2),"change_percent":round(change,1) if change is not None else None,"period_days":days,"note":"Transaction totals show the change; available records do not establish its cause."}

def top_products(db: Session, limit: int = 5):
    rows = db.query(Product.name, func.sum(Sale.quantity).label("units"), func.sum(Sale.quantity*Sale.unit_price).label("revenue")).join(Sale, Sale.product_id==Product.id).group_by(Product.id).order_by(func.sum(Sale.quantity*Sale.unit_price).desc()).limit(limit).all()
    return [{"name": n, "units": int(u), "revenue": round(float(r),2)} for n,u,r in rows]

def search_documents(db: Session, query: str, limit: int = 4):
    stop_words={"about","after","and","are","but","does","for","from","has","have","how","into","is","may","our","say","the","this","what","when","where","which","with","you"}
    terms = {t.lower() for t in re.findall(r"[\w'-]+", query)
             if len(t)>2 and t.lower() not in stop_words}
    query_vector=None
    chunks = db.query(DocumentChunk, Document).join(Document, Document.id==DocumentChunk.document_id).all()
    # Seeded/local documents use lexical retrieval by default. Avoid loading or
    # downloading the embedding model when there are no stored vectors to compare.
    if any(chunk.embedding for chunk, _ in chunks):
        try:
            query_vector=_embed([query])[0]
        except Exception:
            query_vector=None
    scored=[]
    for chunk, doc in chunks:
        text=chunk.content.lower()
        text_terms=re.findall(r"[\w'-]+", text)
        score=sum(text_terms.count(term) for term in terms)
        if query_vector and chunk.embedding:
            import math
            vector=json.loads(chunk.embedding);dot=sum(a*b for a,b in zip(query_vector,vector));norm=math.sqrt(sum(x*x for x in query_vector)*sum(x*x for x in vector));score=max(score,dot/norm if norm else 0)
        if score: scored.append((score, chunk, doc))
    scored.sort(key=lambda x:x[0], reverse=True)
    if scored:
        relevance_floor=scored[0][0]*0.25
        scored=[item for item in scored if item[0]>=relevance_floor]
    return [{"filename": d.filename, "page": c.page, "content": c.content, "score": s} for s,c,d in scored[:limit]]

_encoder=None
def _embed(texts):
    """Encode text when sentence-transformers is installed; callers retain lexical fallback."""
    global _encoder
    if _encoder is None:
        from sentence_transformers import SentenceTransformer
        _encoder=SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder.encode(texts,normalize_embeddings=True).tolist()

def _model_route(text: str) -> str | None:
    """Ask the configured Groq-compatible model to choose one allowlisted business tool."""
    from app.backend.config import settings
    if not settings.groq_api_key or not settings.groq_model:
        return None
    try:
        import httpx
        response=httpx.post(settings.groq_base_url.rstrip("/")+"/chat/completions",headers={"Authorization":f"Bearer {settings.groq_api_key}"},json={"model":settings.groq_model,"temperature":0,"tool_choice":"required","tools":[{"type":"function","function":{"name":"route_business_request","description":"Classify intent and choose the single best read-only business lookup or approval-proposal tool.","parameters":{"type":"object","properties":{"tool":{"type":"string","enum":["get_low_stock_products","get_sales_summary","get_top_products","search_customers","search_documents","prepare_reorder_request","business_report","general_help"]}},"required":["tool"],"additionalProperties":False}}}],"messages":[{"role":"system","content":"Route the user's request to the best listed tool. Document/policy questions use search_documents. Preparing or creating a reorder uses prepare_reorder_request. Never choose an unlisted action."},{"role":"user","content":text}]},timeout=12)
        response.raise_for_status();calls=response.json()["choices"][0]["message"].get("tool_calls",[])
        selected=json.loads(calls[0]["function"]["arguments"]).get("tool") if calls else None
        return selected if selected in {"get_low_stock_products","get_sales_summary","get_top_products","search_customers","search_documents","prepare_reorder_request","business_report","general_help"} else None
    except Exception:
        log.warning("Model tool routing unavailable; using local intent router")
        return None

def route_request(db: Session, text: str):
    q=text.lower(); used=[]; sources=[]; data=None
    model_tool=_model_route(text)
    # The model only selects from this explicit allowlist; local tools retain full control
    # of query execution and the action branch still creates an approval proposal.
    if model_tool:
        q={"prepare_reorder_request":"prepare reorder request "+q,"get_low_stock_products":"inventory "+q,"get_sales_summary":"sales "+q,"get_top_products":"top products "+q,"search_customers":"customer "+q,"search_documents":"policy "+q,"business_report":"business report "+q,"general_help":q}[model_tool]
    if any(x in q for x in ("reorder", "re-order", "restock", "prepare order")):
        products=low_stock(db); used.append("get_low_stock_products")
        return {"kind":"action", "data":[{"product_id":p.id,"product":p.name,"stock":p.stock,"reorder_level":p.reorder_level,"suggested_quantity":max(0,p.reorder_level*2-p.stock)} for p in products],"tools":used,"sources":[]}
    if any(x in q for x in ("policy", "document", "return", "refund", "summarize the uploaded", "knowledge")):
        sources=search_documents(db,text); used.append("search_documents")
        if sources:
            answer="I found relevant material in the knowledge base:\n\n"+"\n\n".join(f"{s['content']}" for s in sources)
        else: answer="The knowledge base does not contain enough information to answer that. Upload a relevant document and try again."
        return {"kind":"knowledge", "answer":answer,"tools":used,"sources":[{"filename":s["filename"],"page":s["page"]} for s in sources]}
    if any(x in q for x in ("low stock", "inventory", "stock", "reorder threshold")):
        data=[{"product":p.name,"category":p.category,"stock":p.stock,"reorder_level":p.reorder_level,"status":"Out of stock" if p.stock==0 else "Critical" if p.stock<=p.reorder_level//2 else "Low"} for p in low_stock(db)]; used.append("get_low_stock_products")
        answer=f"{len(data)} products are at or below their reorder threshold." + ("\n\n"+"\n".join(f"- {p['product']} — {p['stock']} units (reorder at {p['reorder_level']})" for p in data[:12]) if data else " Inventory levels are healthy.")
    elif any(x in q for x in ("customer", "repeat", "inactive")):
        rows=db.query(Customer).all(); data=[{"name":c.name,"segment":c.segment,"email":c.email} for c in rows]; used.append("search_customers"); answer=f"There are {len(data)} customers in the directory. Here are the first results:\n"+"\n".join(f"- {c['name']} ({c['segment']})" for c in data[:10])
    elif any(x in q for x in ("top product", "best seller", "product generated", "selling product")):
        data=top_products(db); used.append("get_top_products"); answer="Top products by recorded revenue:\n"+"\n".join(f"- {p['name']}: ${p['revenue']:,.2f} ({p['units']} units)" for p in data)
    elif any(x in q for x in ("sales", "revenue", "business report", "report", "trend", "declin", "compare")):
        data=sales_summary(db); used.append("get_sales_summary"); answer=f"Recorded revenue over the last {data['days']} days is ${data['revenue']:,.2f} across {data['orders']} transactions, averaging ${data['average_order_value']:,.2f} per transaction."
        if any(x in q for x in ("compare", "declin", "decreas", "trend", "why")):
            comparison=compare_sales(db);data={"summary":data,"comparison":comparison};answer+=f" The prior 30-day period recorded ${comparison['previous_revenue']:,.2f}; the current period recorded ${comparison['current_revenue']:,.2f}."+(f" That is a {abs(comparison['change_percent']):.1f}% {'increase' if comparison['change_percent']>0 else 'decrease'}." if comparison["change_percent"] is not None else " A percentage change is unavailable because there is no prior-period revenue.")+" The transaction totals alone do not establish the cause." 
        if "product" in q: data={"summary":data,"top_products":top_products(db)}; used.append("get_top_products")
    else:
        answer="I can look up inventory, sales and revenue, top products, customers, policy documents, and prepare reorder requests. What would you like to check?"
    # Optional provider synthesis is constrained to tool-returned facts. The deterministic
    # response remains available when credentials are absent or the provider is unavailable.
    from app.backend.config import settings
    if settings.groq_api_key and settings.groq_model and data is not None and used:
        try:
            import httpx
            response=httpx.post(settings.groq_base_url.rstrip("/")+"/chat/completions",headers={"Authorization":f"Bearer {settings.groq_api_key}"},json={"model":settings.groq_model,"temperature":0.2,"messages":[{"role":"system","content":"Answer the user using only the supplied structured business data. Never invent metrics. Be concise and label suggestions as recommendations."},{"role":"user","content":json.dumps({"question":text,"business_data":data},default=str)}]},timeout=15)
            response.raise_for_status();answer=response.json()["choices"][0]["message"]["content"] or answer
        except Exception: log.warning("Groq synthesis unavailable; returning deterministic tool result")
    return {"kind":"answer","answer":answer,"data":data,"tools":used,"sources":sources}
