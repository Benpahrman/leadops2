"""Portal and sandbox live chat with Alex AI agent and inbound email webhook."""

import logging
import re
from fastapi import APIRouter, Depends, HTTPException, status

from ...auth import ClerkUser, get_current_user_optional
from ...domain import State
from ..dependencies import (
    get_storage,
    get_portal_service,
    get_llm_engine,
    get_inbound_watcher,
)
from .helpers import ensure_demo_sandbox
from .models import ChatMessageRequest, InboundEmailWebhookRequest
from .sandboxes import validate_slug

logger = logging.getLogger("api.portal.chat")

router = APIRouter()


@router.post("/api/sandbox/{slug}/chat", tags=["Portal API"])
def chat_with_assistant(
    slug: str,
    req: ChatMessageRequest,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
    llm_engine=Depends(get_llm_engine),
):
    """Real-time conversation with the Alex AI persona regarding portal specs and fields."""
    slug = validate_slug(slug)
    try:
        sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
        lead = sandbox.lead
        if lead.state == State.OUTREACH_SENT:
            lead.transition(State.CONVERSATIONAL_INTAKE, "Customer started a conversation with Alex")
            storage_backend.save_lead(lead)

        # 1. Retrieve persistent conversation history from storage
        conversation_history = []
        if hasattr(storage_backend, "list_chat_messages"):
            conversation_history = storage_backend.list_chat_messages(slug, limit=20)
        
        # 2. Append client-provided transient history if provided
        if req.history:
            conversation_history.extend(req.history)

        # 3. Record incoming customer message in storage
        if hasattr(storage_backend, "record_chat_message"):
            storage_backend.record_chat_message(slug, "user", req.message)

        # Check if customer provided a target URL in chat
        url_match = re.search(r"https?://[^\s]+", req.message)
        if url_match:
            chat_target_url = url_match.group(0).rstrip(".,;)")
            lead.source_url = chat_target_url
            sandbox.source_url = chat_target_url
            storage_backend.save_lead(lead)
            storage_backend.save_sandbox(sandbox)
            logger.info(f"🎯 [CHAT TARGET URL DETECTED] Customer specified target: {chat_target_url} for {lead.lead_id}")

        context = {
            "slug": slug,
            "company_name": getattr(lead, "company_name", slug),
            "jurisdiction": getattr(lead, "jurisdiction", "County Registry"),
            "source_url": sandbox.source_url,
            "tier": lead.tier.name,
            "selected_fields": lead.selected_fields or [],
        }

        # 4. Generate dynamic, non-repetitive response aware of prior dialogue
        reply = llm_engine.chat_with_alex(req.message, context, conversation_history=conversation_history)

        # 5. Record Alex's generated reply in storage
        if hasattr(storage_backend, "record_chat_message"):
            storage_backend.record_chat_message(slug, "alex", reply)

        # 6. Alert operator of live customer chat
        try:
            from ...notifications import notification_manager
            notification_manager.notify_chat_message(
                slug=slug,
                sender_role="user",
                message_text=req.message,
                ai_reply_text=reply,
                lead=lead,
            )
        except Exception as notif_err:
            logger.warning(f"Chat notification notice: {notif_err}")

        return {"ok": True, "reply": reply}
    except Exception as e:
        logger.error(f"Chat error for slug {slug}: {e}")
        return {
            "ok": True,
            "reply": "I've noted that requirement for our dev swarm. Our autonomous pipeline will verify that schema before deployment!"
        }


@router.get("/api/sandbox/{slug}/chat", tags=["Portal API"])
def get_chat_history(
    slug: str,
    storage_backend=Depends(get_storage),
):
    """Retrieve running conversation log for a sandbox."""
    slug = validate_slug(slug)
    messages = []
    if hasattr(storage_backend, "list_chat_messages"):
        messages = storage_backend.list_chat_messages(slug, limit=50)
    return {"ok": True, "messages": messages}


@router.post("/api/chat", tags=["Portal API"])
def chat_general(
    req: ChatMessageRequest,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
    llm_engine=Depends(get_llm_engine),
):
    """Universal chat endpoint for visitors across landing and dashboard pages."""
    return chat_with_assistant(
        slug="lead-apex-roofing",
        req=req,
        user=user,
        portal_service=portal_service,
        storage_backend=storage_backend,
        llm_engine=llm_engine,
    )


@router.get("/api/chat", tags=["Portal API"])
def get_general_chat_history(
    storage_backend=Depends(get_storage),
):
    """Retrieve running general chat log."""
    return get_chat_history(slug="lead-apex-roofing", storage_backend=storage_backend)


@router.post("/api/email/inbound", tags=["Email"])
def receive_inbound_email_webhook(
    payload: InboundEmailWebhookRequest,
    inbound_watcher=Depends(get_inbound_watcher),
):
    """Receive incoming email via HTTP webhook (Cloudflare Email Routing, SendGrid, Mailgun, Postmark)."""
    if not inbound_watcher:
        raise HTTPException(status_code=503, detail="Inbound email subsystem not initialized")

    result = inbound_watcher.process_single_inbound_email({
        "sender_email": payload.sender,
        "sender_name": payload.sender_name or "",
        "subject": payload.subject,
        "body_text": payload.body,
        "body_html": "",
        "message_id": payload.message_id or "",
    })
    return {"ok": True, "result": result}
