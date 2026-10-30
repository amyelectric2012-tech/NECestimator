import re
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.models import Project, User
from app.models.takeoff import TakeoffItem
from app.services.load_calc.engine import LoadCalcEngine
from app.services.takeoff.generator import generate_takeoff_from_calculation

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    actions: list[str] = []


def _project(db, project_id, user):
    p = db.query(Project).filter(Project.id == str(project_id), Project.owner_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.post("", response_model=ChatResponse)
def chat(project_id: UUID, payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project = _project(db, project_id, current_user)
    msg = payload.message.strip().lower()
    actions = []

    # help
    if msg in ("help", "?"):
        return ChatResponse(reply=(
            "Commands:\n"
            "- generate takeoff\n"
            "- calculate\n"
            "- summary / total\n"
            "- add <qty> <description> [at $<cost>]\n"
            "- list items\n"
            "- clear takeoff\n"
            "- nec <query>  (search NEC 2017 code book)\n"
            "- describe <work>  (generate estimate from description)"
        ), actions=[])

    # generate takeoff
    if "generate" in msg and "takeoff" in msg or msg == "generate":
        from app.services.load_calc.schemas import LoadCalcRequest as LCR
        req = LCR(
            project_type=project.project_type if project.project_type in ("single_family", "multi_family", "adu", "duplex") else "single_family",
            floor_area_sqft=project.floor_area_sqft or 1500.0,
        )
        calc = LoadCalcEngine().calculate(req)[0]
        items = generate_takeoff_from_calculation(project.id, calc, project.floor_area_sqft or 1500.0)
        for it in items:
            db.add(TakeoffItem(
                project_id=str(project.id), description=it.description, category=it.category,
                quantity=it.quantity, unit=it.unit, unit_cost=it.unit_cost, labor_hours=it.labor_hours,
                is_auto_generated=True, notes=it.notes,
            ))
        db.commit()
        actions.append(f"generated {len(items)} takeoff items")
        return ChatResponse(reply=f"Generated {len(items)} takeoff items from load calculation.", actions=actions)

    # calculate
    if "calculate" in msg:
        from app.services.load_calc.schemas import LoadCalcRequest as LCR
        req = LCR(
            project_type=project.project_type if project.project_type in ("single_family", "multi_family", "adu", "duplex") else "single_family",
            floor_area_sqft=project.floor_area_sqft or 1500.0,
        )
        calc = LoadCalcEngine().calculate(req)[0]
        return ChatResponse(reply=f"Recommended service: {calc.recommended_service_amps}A. Standard method total: {calc.total_va} VA.", actions=["calculated load"])

    # summary / total
    if "summary" in msg or "total" in msg:
        items = db.query(TakeoffItem).filter(TakeoffItem.project_id == str(project_id)).all()
        total_mat = sum(Decimal(str(i.unit_cost)) * Decimal(str(i.quantity)) for i in items)
        total_h = sum(i.quantity * i.labor_hours for i in items)
        return ChatResponse(reply=f"{len(items)} items | Material: ${total_mat:.2f} | Labor hours: {total_h:.2f}", actions=[])

    # list items
    if "list" in msg:
        items = db.query(TakeoffItem).filter(TakeoffItem.project_id == str(project_id)).all()
        lines = [f"- {i.description} (qty {i.quantity})" for i in items[:20]]
        return ChatResponse(reply="\n".join(lines) if lines else "No items yet.", actions=[])

    # clear takeoff
    if "clear" in msg:
        db.query(TakeoffItem).filter(TakeoffItem.project_id == str(project_id)).delete()
        db.commit()
        actions.append("cleared takeoff")
        return ChatResponse(reply="Takeoff cleared.", actions=actions)

    # NEC code book search
    if msg.startswith(("nec ", "code ")):
        q = msg.split(" ", 1)[1].strip()
        import re as _re

        from app.routers.nec_reference import load_text
        text = load_text()
        if not text:
            return ChatResponse(reply="NEC text not loaded.", actions=[])
        low = text.lower()
        needle = q.lower()
        positions = []
        start = 0
        while True:
            idx = low.find(needle, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + len(q)
            if len(positions) >= 5:
                break
        if not positions:
            return ChatResponse(reply=f"No NEC matches for '{q}'.", actions=[])
        snippets = []
        for idx in positions[:3]:
            s = max(0, idx - 120)
            e = min(len(text), idx + len(q) + 240)
            snip = _re.sub(r"\\s{2,}", " ", text[s:e].replace("\\n", " "))
            snippets.append(f"…{snip}…")
        return ChatResponse(reply=f"NEC 2017 matches for '{q}' ({len(positions)} total):\n\n" + "\n\n".join(snippets), actions=["nec search"])

    # describe <work> -> estimate from description
    if msg.startswith(("describe ", "estimate ")):
        desc = msg.split(" ", 1)[1].strip()
        from app.services.takeoff.from_description import generate_from_description
        items, refs = generate_from_description(project, desc)
        for it in items:
            db.add(TakeoffItem(
                project_id=str(project.id), description=it["description"], category=it["category"],
                quantity=it["quantity"], unit=it["unit"], unit_cost=it["unit_cost"],
                labor_hours=it["labor_hours"], is_auto_generated=it.get("is_auto_generated", False),
                notes=it.get("notes"),
            ))
        db.commit()
        actions.append(f"added {len(items)} items")
        reply = f"Generated {len(items)} takeoff items from description.\n"
        if refs:
            reply += "\nNEC references:\n" + "\n".join(f"- {r}" for r in refs[:3])
        return ChatResponse(reply=reply, actions=actions)

    # add <qty> <description> [at $<cost>]
    m = re.match(r"add\s+(\d+(?:\.\d+)?)\s+(.+?)(?:\s+at\s+\$?(\d+(?:\.\d+)?))?$", msg)
    if m:
        qty = float(m.group(1))
        desc = m.group(2).strip()
        cost = float(m.group(3)) if m.group(3) else 0.0
        row = TakeoffItem(
            project_id=str(project.id), description=desc.title(), category="misc",
            quantity=qty, unit="ea", unit_cost=Decimal(str(cost)), labor_hours=0.0,
            is_auto_generated=False, notes="Added via chat",
        )
        db.add(row)
        db.commit()
        actions.append(f"added {qty} x {desc}")
        return ChatResponse(reply=f"Added {qty} x {desc} (unit cost ${cost:.2f}).", actions=actions)

    # fallback: search NEC code book
    import re as _re

    from app.routers.nec_reference import load_text
    text = load_text()
    if text and len(msg) >= 3:
        low = text.lower()
        idx = low.find(msg)
        if idx != -1:
            s = max(0, idx - 150)
            e = min(len(text), idx + len(msg) + 300)
            snip = _re.sub(r"\\s{2,}", " ", text[s:e].replace("\\n", " "))
            return ChatResponse(reply=f"NEC 2017 match for '{msg}':\n…{snip}…", actions=["nec search"])
    return ChatResponse(reply="I didn't understand that. Type 'help' for commands, or 'nec <query>' to search the code book.", actions=[])
