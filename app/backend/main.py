import json, logging, os, tempfile
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.backend.database import Base, engine, get_db
from app.backend.models import User, Product, Customer, Sale, Document, DocumentChunk, AgentRun, AgentToolCall, Approval, AuditLog, AutomationLog, Conversation, Message
from app.backend.auth import current_user, roles, verify_password, token_for, hash_password
from app.backend.config import settings
from app.backend.services import audit, low_stock, sales_summary, top_products, revenue_trend, route_request

logging.basicConfig(level=logging.INFO)
Base.metadata.create_all(bind=engine)
app=FastAPI(title="AI Business Operations Copilot", version="1.0.0", description="Auditable AI-enabled operations API")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class Login(BaseModel): email:str; password:str
class Chat(BaseModel): message:str=Field(min_length=1,max_length=5000); conversation_id:int|None=None
class Decision(BaseModel): note:str=""

@app.get("/health")
def health(): return {"status":"ok","demo_mode":settings.demo_mode}

@app.post("/auth/login")
def login(body:Login,db:Session=Depends(get_db)):
    user=db.query(User).filter(User.email==body.email.lower()).first()
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Email or password is incorrect")
    audit(db,user.id,"login","session")
    return {"access_token":token_for(user),"token_type":"bearer","user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

@app.post("/auth/register")
def register(body:Login,db:Session=Depends(get_db)):
    if db.query(User).filter_by(email=body.email.lower()).first(): raise HTTPException(409,"Email is already registered")
    user=User(email=body.email.lower(),name=body.email.split("@")[0],password_hash=hash_password(body.password),role="employee"); db.add(user); db.commit(); db.refresh(user)
    return {"access_token":token_for(user),"token_type":"bearer"}

@app.get("/auth/me")
def me(u:User=Depends(current_user)): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role}

@app.get("/conversations")
def conversations(db:Session=Depends(get_db),u:User=Depends(current_user)):
    return [{"id":c.id,"title":c.title,"created_at":c.created_at.isoformat()} for c in db.query(Conversation).filter_by(user_id=u.id).order_by(Conversation.created_at.desc()).limit(100).all()]

@app.get("/conversations/{conversation_id}")
def conversation_detail(conversation_id:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=db.get(Conversation,conversation_id)
    if not c or c.user_id!=u.id:raise HTTPException(404,"Conversation not found")
    return {"id":c.id,"title":c.title,"messages":[{"role":m.role,"content":m.content,"created_at":m.created_at.isoformat()} for m in db.query(Message).filter_by(conversation_id=c.id).order_by(Message.created_at).all()]}

@app.get("/dashboard/summary")
def dashboard(db:Session=Depends(get_db),u:User=Depends(current_user)):
    totals=sales_summary(db); return {**totals,"customers":db.query(Customer).count(),"low_stock":len(low_stock(db)),"top_products":top_products(db),"inventory_value":round(sum(p.stock*p.cost for p in db.query(Product).all()),2)}

@app.get("/products")
def products(search:str="",category:str="",db:Session=Depends(get_db),u:User=Depends(current_user)):
    query=db.query(Product)
    if search: query=query.filter(Product.name.ilike(f"%{search}%"))
    if category: query=query.filter(Product.category==category)
    return [{"id":p.id,"sku":p.sku,"name":p.name,"category":p.category,"price":p.price,"cost":p.cost,"stock":p.stock,"reorder_level":p.reorder_level,"status":"Out of Stock" if p.stock==0 else "Critical" if p.stock<=p.reorder_level/2 else "Low" if p.stock<=p.reorder_level else "Healthy"} for p in query.order_by(Product.name).all()]

@app.get("/inventory")
def inventory(db:Session=Depends(get_db),u:User=Depends(current_user)): return products(db=db,u=u)
@app.get("/inventory/low-stock")
def inventory_low(db:Session=Depends(get_db),u:User=Depends(current_user)): return [{"id":p.id,"name":p.name,"stock":p.stock,"reorder_level":p.reorder_level} for p in low_stock(db)]
@app.get("/sales")
def sales(days:int=90,db:Session=Depends(get_db),u:User=Depends(current_user)):
    from datetime import timedelta
    since=datetime.now(timezone.utc)-timedelta(days=max(1,min(days,3650)))
    return [{"id":s.id,"customer":db.get(Customer,s.customer_id).name,"product":db.get(Product,s.product_id).name,"quantity":s.quantity,"unit_price":s.unit_price,"revenue":round(s.quantity*s.unit_price,2),"sold_at":s.sold_at.isoformat()} for s in db.query(Sale).filter(Sale.sold_at>=since).order_by(Sale.sold_at.desc()).limit(1000).all()]
@app.get("/sales/summary")
def sales_route(days:int=30,db:Session=Depends(get_db),u:User=Depends(current_user)): return {**sales_summary(db,days),"top_products":top_products(db)}
@app.get("/sales/trend")
def sales_trend_route(days:int=90,db:Session=Depends(get_db),u:User=Depends(current_user)):
    return revenue_trend(db,days)
@app.get("/reports/business")
def business_report(days:int=7,db:Session=Depends(get_db),u:User=Depends(current_user)):
    summary=sales_summary(db,days);products=top_products(db);low=low_stock(db)
    lines=[f"# Business report — last {days} days", "", f"- Revenue: ${summary['revenue']:,.2f}",f"- Transactions: {summary['orders']}",f"- Average transaction: ${summary['average_order_value']:,.2f}",f"- Customers: {db.query(Customer).count()}","", "## Leading products"]
    lines += [f"- {p['name']}: ${p['revenue']:,.2f} ({p['units']} units)" for p in products]
    lines += ["", "## Inventory attention"]+[f"- {p.name}: {p.stock} on hand; reorder threshold {p.reorder_level}" for p in low]
    lines += ["", "## Suggested review", "Review products at or below their reorder threshold and route any purchase proposal through the approval queue."]
    audit(db,u.id,"report_generated","business",f"{days} days")
    return {"markdown":"\n".join(lines),"metrics":summary,"top_products":products,"low_stock_count":len(low)}
@app.get("/customers")
def customers(search:str="",db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(Customer)
    if search:q=q.filter(Customer.name.ilike(f"%{search}%"))
    return [{"id":c.id,"name":c.name,"email":c.email,"segment":c.segment,"orders":db.query(Sale).filter_by(customer_id=c.id).count()} for c in q.order_by(Customer.name).all()]
@app.get("/customers/{customer_id}")
def customer_detail(customer_id:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    c=db.get(Customer,customer_id)
    if not c:raise HTTPException(404,"Customer not found")
    entries=db.query(Sale).filter_by(customer_id=c.id).all()
    return {"id":c.id,"name":c.name,"email":c.email,"segment":c.segment,"orders":len(entries),"spend":round(sum(x.quantity*x.unit_price for x in entries),2)}
@app.get("/orders")
def orders(db:Session=Depends(get_db),u:User=Depends(current_user)):
    return [{"id":s.id,"customer":db.get(Customer,s.customer_id).name,"product":db.get(Product,s.product_id).name,"total":round(s.quantity*s.unit_price,2),"created_at":s.sold_at.isoformat()} for s in db.query(Sale).order_by(Sale.sold_at.desc()).limit(300).all()]

def extract_upload(name:str,raw:bytes):
    ext=name.lower().rsplit(".",1)[-1]
    if ext in ("txt","md"): return [(None,raw.decode("utf-8",errors="replace"))]
    if ext=="pdf":
        import fitz
        doc=fitz.open(stream=raw,filetype="pdf"); return [(i+1,p.get_text()) for i,p in enumerate(doc)]
    if ext=="docx":
        from docx import Document as Word
        return [(None,"\n".join(p.text for p in Word(tempfile.SpooledTemporaryFile()).paragraphs))] if False else [(None, _docx_text(raw))]
    raise HTTPException(415,"Supported file types: PDF, TXT, Markdown, DOCX")

def _docx_text(raw):
    import io
    from docx import Document as Word
    return "\n".join(p.text for p in Word(io.BytesIO(raw)).paragraphs)

@app.post("/documents/upload")
async def upload(file:UploadFile=File(...),db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):
    raw=await file.read(settings.max_upload_mb*1024*1024+1)
    if len(raw)>settings.max_upload_mb*1024*1024:raise HTTPException(413,"File exceeds upload size limit")
    try: pages=extract_upload(file.filename or "document.txt",raw)
    except HTTPException:raise
    except Exception as e:logging.exception("Document extraction failed");raise HTTPException(422,"Unable to read this document") from e
    doc=Document(filename=(file.filename or "document")[:255],content_type=file.content_type or "application/octet-stream",uploaded_by=u.id,status="processed");db.add(doc);db.flush()
    all_chunks=[]
    for page,text in pages:
        words=text.split()
        for i in range(0,len(words),220):
            chunk=" ".join(words[i:i+220])
            if chunk:all_chunks.append((page,chunk))
    vectors=[]
    try:
        from app.backend.services import _embed
        vectors=_embed([chunk for _,chunk in all_chunks])
    except Exception:logging.info("Semantic embeddings unavailable; document will use lexical retrieval")
    for index,(page,chunk) in enumerate(all_chunks):db.add(DocumentChunk(document_id=doc.id,page=page,content=chunk,embedding=json.dumps(vectors[index]) if vectors else None))
    doc.chunk_count=db.query(DocumentChunk).filter_by(document_id=doc.id).count();db.commit();db.refresh(doc);audit(db,u.id,"document_upload",doc.filename,f"{doc.chunk_count} chunks")
    return {"id":doc.id,"filename":doc.filename,"chunk_count":doc.chunk_count,"status":doc.status}

@app.get("/documents")
def documents(db:Session=Depends(get_db),u:User=Depends(current_user)):return [{"id":d.id,"filename":d.filename,"content_type":d.content_type,"status":d.status,"chunk_count":d.chunk_count,"created_at":d.created_at.isoformat()} for d in db.query(Document).order_by(Document.created_at.desc()).all()]
@app.delete("/documents/{doc_id}")
def delete_document(doc_id:int,db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):
    doc=db.get(Document,doc_id)
    if not doc:raise HTTPException(404,"Document not found")
    db.query(DocumentChunk).filter_by(document_id=doc_id).delete();db.delete(doc);db.commit();audit(db,u.id,"document_delete",str(doc_id));return {"status":"deleted"}

@app.post("/rag/query")
def rag(body:Chat,db:Session=Depends(get_db),u:User=Depends(current_user)):
    from app.backend.services import search_documents
    hits=search_documents(db,body.message);audit(db,u.id,"rag_retrieval","documents",f"{len(hits)} chunks")
    return {"answer":"\n\n".join(h["content"] for h in hits) if hits else "The knowledge base does not contain enough information to answer that.","sources":[{"filename":h["filename"],"page":h["page"]} for h in hits]}

@app.post("/copilot/chat")
@app.post("/agent/run")
def chat(body:Chat,db:Session=Depends(get_db),u:User=Depends(current_user)):
    from app.backend.services import route_request
    conversation=db.get(Conversation,body.conversation_id) if body.conversation_id else None
    if conversation and conversation.user_id!=u.id:raise HTTPException(404,"Conversation not found")
    if conversation is None:
        conversation=Conversation(user_id=u.id,title=body.message[:75]);db.add(conversation);db.flush()
    db.add(Message(conversation_id=conversation.id,role="user",content=body.message))
    result=route_request(db,body.message);run=AgentRun(user_id=u.id,request=body.message,response=result.get("answer", "Prepared a reorder proposal."),status="completed");db.add(run);db.flush()
    for tool in result["tools"]:db.add(AgentToolCall(run_id=run.id,tool_name=tool,result_summary=json.dumps(result.get("data",{}),default=str)[:1000]))
    approval=None
    if result["kind"]=="action":
        approval=Approval(requested_by=u.id,action_type="reorder_request",payload=json.dumps(result["data"]));db.add(approval);db.flush();result["approval"]={"id":approval.id,"status":"pending"};result["answer"]="I prepared a reorder proposal for approval. Review quantities and approve it in the Approvals workspace before any action is sent."
        audit(db,u.id,"approval_created",str(approval.id),"reorder_request")
    db.add(Message(conversation_id=conversation.id,role="assistant",content=result.get("answer", "Prepared a reorder proposal.")))
    db.commit();result["run_id"]=run.id;result["conversation_id"]=conversation.id;result["tools"]=[{"name":x} for x in result["tools"]];return result

@app.get("/agent/runs/{run_id}")
def run_detail(run_id:int,db:Session=Depends(get_db),u:User=Depends(current_user)):
    run=db.get(AgentRun,run_id)
    if not run or (run.user_id!=u.id and u.role!="admin"):raise HTTPException(404,"Agent run not found")
    return {"id":run.id,"request":run.request,"response":run.response,"status":run.status,"tools":[x.tool_name for x in db.query(AgentToolCall).filter_by(run_id=run.id).all()]}

@app.get("/approvals")
def approvals(db:Session=Depends(get_db),u:User=Depends(current_user)):
    q=db.query(Approval)
    if u.role=="employee":q=q.filter_by(requested_by=u.id)
    return [{"id":a.id,"action_type":a.action_type,"payload":json.loads(a.payload),"status":a.status,"created_at":a.created_at.isoformat(),"requested_by":db.get(User,a.requested_by).name,"decision_note":a.decision_note} for a in q.order_by(Approval.created_at.desc()).all()]

def decide(approval_id:int,body:Decision,db:Session,u:User,approve:bool):
    item=db.get(Approval,approval_id)
    if not item:raise HTTPException(404,"Approval not found")
    if item.status!="pending":raise HTTPException(409,"This approval has already been decided")
    item.status="approved" if approve else "rejected";item.decided_by=u.id;item.decision_note=body.note;item.decided_at=datetime.now(timezone.utc);db.flush()
    status="simulated";summary="Demo mode: external action was safely simulated."
    if approve and not settings.demo_mode:
        if not settings.n8n_webhook_url:status="not_configured";summary="Approval saved, but N8N_WEBHOOK_URL is not configured."
        else:
            import httpx
            try:
                headers={"Authorization":f"Bearer {settings.n8n_api_key}"} if settings.n8n_api_key else {}
                response=httpx.post(settings.n8n_webhook_url,json={"approval_id":item.id,"action_type":item.action_type,"payload":json.loads(item.payload)},headers=headers,timeout=12);response.raise_for_status();status="sent";summary="Approved action delivered to the configured workflow."
            except Exception:logging.exception("Automation webhook failed");status="failed";summary="Approval recorded; automation delivery failed. Check service logs."
    db.add(AutomationLog(approval_id=item.id,event=item.action_type,status=status,response_summary=summary));audit(db,u.id,"approval_decision",str(item.id),item.status);db.commit()
    return {"id":item.id,"status":item.status,"automation_status":status,"message":summary}
@app.post("/approvals/{approval_id}/approve")
def approve(approval_id:int,body:Decision,db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):return decide(approval_id,body,db,u,True)
@app.post("/approvals/{approval_id}/reject")
def reject(approval_id:int,body:Decision,db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):return decide(approval_id,body,db,u,False)
@app.post("/automation/trigger")
def automation(body:dict,db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):raise HTTPException(403,"External automation can only be triggered through an approved action")
@app.get("/automations/logs")
def automation_logs(db:Session=Depends(get_db),u:User=Depends(current_user)):return [{"id":x.id,"event":x.event,"status":x.status,"summary":x.response_summary,"created_at":x.created_at.isoformat()} for x in db.query(AutomationLog).order_by(AutomationLog.created_at.desc()).all()]
@app.get("/audit-logs")
def audit_logs(db:Session=Depends(get_db),u:User=Depends(roles("admin","manager"))):return [{"id":a.id,"timestamp":a.created_at.isoformat(),"user":db.get(User,a.user_id).name if a.user_id and db.get(User,a.user_id) else "System","event":a.event,"resource":a.resource,"status":a.status,"details":a.details} for a in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(500).all()]
