import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import settings


def generate_pdf(project, estimate, load_calcs) -> str:
    os.makedirs(settings.pdf_dir, exist_ok=True)
    path = os.path.join(settings.pdf_dir, f"{project.id}_{estimate.id}.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.8*inch, rightMargin=0.8*inch,
                            topMargin=0.8*inch, bottomMargin=0.8*inch)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=12)
    h = ParagraphStyle("h", parent=styles["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=6)
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=9)

    story = []
    story.append(Paragraph("Electrical Estimate — Preliminary", title))
    story.append(Paragraph("PRELIMINARY — NOT FOR CONSTRUCTION", ParagraphStyle("warn", parent=body, textColor=colors.red, fontSize=11, spaceAfter=12)))
    story.append(Paragraph(f"Project: {project.name}", body))
    client = getattr(project, "client", None)
    if client is not None:
        story.append(Paragraph(f"Client: {client.name}" + (f" | {client.email}" if client.email else "") + (f" | {client.phone}" if client.phone else ""), body))
        if client.address:
            story.append(Paragraph(f"Address: {client.address}", body))
    story.append(Paragraph(f"Type: {project.project_type} | Floor area: {project.floor_area_sqft} sqft | Units: {project.num_units}", body))
    story.append(Paragraph(f"Generated: {estimate.created_at}", small))
    story.append(Spacer(1, 12))

    # Scope of work
    story.append(Paragraph("Scope of Work", h))
    story.append(Paragraph(estimate.scope_of_work or "Residential electrical installation per NEC 2017.", body))
    story.append(Spacer(1, 8))

    # Load calc summary
    story.append(Paragraph("Load Calculation Summary", h))
    lc_data = [["Method", "Total VA", "Total Amps", "Recommended Service"]]
    for method, lc in (load_calcs or {}).items():
        r = lc.get("results", {}) if isinstance(lc, dict) else {}
        lc_data.append([method, f"{r.get('total_va', 0):,.0f}", f"{r.get('total_amps', 0):.1f}", f"{r.get('recommended_service_amps', 0)}A"])
    if len(lc_data) > 1:
        t = Table(lc_data, colWidths=[1.6*inch, 1.2*inch, 1.2*inch, 1.6*inch])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                               ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]))
        story.append(t)
    story.append(Spacer(1, 8))

    # Detailed side-by-side for standard
    std = (load_calcs or {}).get("standard", {})
    if std:
        r = std.get("results", {})
        story.append(Paragraph("Standard Method (NEC 220 Part III) Detail", h))
        rows = [
            ["General lighting (3 VA/sqft)", f"{r.get('general_lighting_va', 0):,.0f}"],
            ["Small-appliance", f"{r.get('small_appliance_va', 0):,.0f}"],
            ["Laundry", f"{r.get('laundry_va', 0):,.0f}"],
            ["Lighting load (before demand)", f"{r.get('lighting_load_va', 0):,.0f}"],
            ["Lighting demand (Tbl 220.42)", f"{r.get('lighting_demand_va', 0):,.0f}"],
            ["Fastened appliances (connected)", f"{r.get('fastened_appliances_va', 0):,.0f}"],
            ["Fastened appliances (demand)", f"{r.get('fastened_demand_va', 0):,.0f}"],
            ["Ranges (connected)", f"{r.get('range_connected_va', 0):,.0f}"],
            ["Ranges (demand, Tbl 220.55)", f"{r.get('range_demand_va', 0):,.0f}"],
            ["Dryers (connected)", f"{r.get('dryer_connected_va', 0):,.0f}"],
            ["Dryers (demand, Tbl 220.54)", f"{r.get('dryer_demand_va', 0):,.0f}"],
            ["HVAC (noncoincident)", f"{r.get('hvac_va', 0):,.0f}"],
            ["Motor adder (25%)", f"{r.get('motor_adder_va', 0):,.0f}"],
            ["Total VA", f"{r.get('total_va', 0):,.0f}"],
            ["Total Amps (240V)", f"{r.get('total_amps', 0):.1f}"],
            ["Neutral VA", f"{r.get('neutral_va', 0):,.0f}"],
        ]
        t = Table(rows, colWidths=[3.5*inch, 1.5*inch])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Bold")]))
        story.append(t)
        story.append(Spacer(1, 8))

    # Material list
    story.append(Paragraph("Material Takeoff", h))
    items = estimate.line_items or []
    data = [["Item", "Qty", "Unit", "Unit Cost", "Total"]]
    for li in items:
        data.append([li.get("name", ""), str(li.get("qty", 0)), li.get("unit", "ea"),
                     f"${li.get('unit_cost', 0):.2f}", f"${li.get('line_total', 0):.2f}"])
    data.append(["", "", "", "Materials", f"${estimate.total_materials:,.2f}"])
    if len(data) > 2:
        t = Table(data, colWidths=[2.6*inch, 0.6*inch, 0.6*inch, 0.9*inch, 0.9*inch])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                               ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                               ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
        story.append(t)
    story.append(Spacer(1, 8))

    # Cost summary
    story.append(Paragraph("Cost Summary", h))
    labor_rate = getattr(project, "labor_rate", None)
    try:
        labor_rate = float(labor_rate) if labor_rate is not None else 85.0
    except (TypeError, ValueError):
        labor_rate = 85.0
    labor_cost = estimate.total_labor_hours * labor_rate
    summary = [
        ["Materials", f"${estimate.total_materials:,.2f}"],
        ["Labor", f"${labor_cost:,.2f} ({estimate.total_labor_hours:,.2f} hrs @ ${labor_rate:.2f}/hr)"],
        [f"Markup ({estimate.markup_pct*100:.0f}%)", ""],
        [f"Contingency ({estimate.contingency_pct*100:.0f}%)", ""],
        [f"Tax ({estimate.tax_pct*100:.0f}%)", ""],
        ["Grand Total", f"${estimate.total_cost:,.2f}"],
    ]
    # labor summary
    if estimate.labor_summary:
        story.append(Paragraph("Labor Hours by Category", h))
        ls = [["Category", "Hours"]]
        for k, v in estimate.labor_summary.items():
            ls.append([k, f"{v:.2f}"])
        t = Table(ls, colWidths=[3*inch, 1.5*inch])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                               ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                               ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]))
        story.append(t)
        story.append(Spacer(1, 8))

    t = Table(summary, colWidths=[3.5*inch, 1.5*inch])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                           ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Bold")]))
    story.append(t)
    story.append(Spacer(1, 12))

    # Assumptions
    story.append(Paragraph("Assumptions", h))
    assum = getattr(estimate, "assumptions", None) or ""
    if assum:
        for line in assum.split("\n"):
            story.append(Paragraph(f"• {line}", small))
    else:
        for a in [
            "Calculations per NEC 2017 Article 220 (residential).",
            "Preliminary estimate; field verification required.",
            "Unit costs and labor hours are placeholders/editable.",
            "Neutral load excludes 240V HVAC/motor loads.",
        ]:
            story.append(Paragraph(f"• {a}", small))
    story.append(Spacer(1, 8))
    story.append(Paragraph("NEC notes: " + "; ".join(load_calcs.get("standard", {}).get("results", {}).get("notes", []) if isinstance(load_calcs.get("standard"), dict) else []), small))
    story.append(Spacer(1, 8))
    story.append(Paragraph("NEC 2017 References", h))
    for ref in [
        "Art. 220.12 – Lighting load (3 VA/sqft)",
        "Table 220.42 – Lighting demand factors",
        "220.14 – Small-appliance & laundry loads",
        "Table 220.54 – Dryer demand",
        "Table 220.55 – Range demand",
        "220.60 – Noncoincident loads",
        "220.50/220.18 – Motor loads",
        "Art. 250 – Grounding & bonding",
        "Art. 310 – Conductor sizing",
        "Art. 210.8 / 210.12 – GFCI & AFCI",
    ]:
        story.append(Paragraph(f"• {ref}", small))

    doc.build(story)
    return path
