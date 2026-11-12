# AMY Electric — NEC-Based Estimator: Developer To-Do List

Companion to `AGENTS.md`. Tracks remaining work against the development assignment.
Current repo: FastAPI + React/Vite, Postgres, Alembic. NEC 2017 full text ingested (3,535 chunks, 100% coverage).

## Already complete
- Auth (JWT, bcrypt), projects, clients, estimates, takeoff, load calc (NEC 220), PDF export, NEC reference search (full code book), CRM dashboard + pipeline + activities, EV charger & 200A service upgrade takeoff generators, pricing engine (materials/labor/overhead/markup/contingency/tax/profit/margin), calculation audit records, pagination, E2E smoke tests.

## Stage 1 — EV charger & 200A service upgrade (first milestone) — P1
**Goal:** end-to-end EV charger + 200A service upgrade with full NEC traceability.

- [ ] `backend/app/services/nec_calc/voltage_drop.py` — voltage-drop calc (NEC 210.19(A)(1) note, 215.2(A)(1) note) for copper/aluminum, given amps, length, conductor size, temp.
- [ ] `backend/app/services/nec_calc/ampacity.py` — conductor ampacity from NEC 310.15(B)(16) (75°C default) with temp correction (310.15(B)(2)) and adjustment (310.15(B)(3)(a)) factors.
- [ ] `backend/app/services/nec_calc/conduit_fill.py` — Chapter 9 Table 1/4/5 fill for EMT/PVC/rigid.
- [ ] EV module: panel capacity check (existing load + EV load vs service rating), breaker sizing (125% continuous per 210.20(A) / 625.42), conductor sizing, voltage-drop warning, conduit sizing, grounding/bonding (250.122, 625.54 GFCI).
- [ ] Service upgrade module: service load calc (220.82/83), service conductor sizing (230.23/310.15), mast height/clearance (230.24), GEC sizing (250.66), grounding electrode (250.50/52/53), main bonding jumper (250.28).
- [ ] Each calculation returns `{value, nec_reference, inputs, warnings}` and persists to `calculation_records`.
- [ ] Tests: `tests/test_ev_charger.py`, `tests/test_service_upgrade.py` with verified NEC examples and acceptance values.
- [ ] Frontend: dedicated EV charger and Service Upgrade wizards (inputs → calc → takeoff → estimate → PDF).

**Acceptance:** EV charger 48A/80ft/EMT and 200A overhead service produce traceable calcs + complete estimate + PDF.

## Stage 2 — NEC rules engine (edition-aware) — P1
- [ ] `nec_rules` table: rule_id, edition, article, section, title, condition (JSON), params (JSON), formula_key, source.
- [ ] `code_editions` table: edition code, adopted date, jurisdiction, amendments.
- [ ] `jurisdiction`/`nec_edition`/`ahj` wired into Project and calculation engine (currently columns exist).
- [ ] California amendments layer (CEC) overrides stored separately and applied when jurisdiction=CA.
- [ ] Engine dispatches by edition; warnings when info missing; "electrician review required" flag.
- [ ] Tests per edition; never hardcode NEC in frontend.

## Stage 3 — Labor production database — P1
- [ ] `labor_assemblies` table: assembly_id, task, unit, hours_per_unit, crew_size, classification, difficulty multipliers, height/access/occupied adjustments.
- [ ] Seed common assemblies (conduit/ft, wire pull/ft, panel, breaker, receptacle, fixture, disconnect, ground rod, EV charger, transformer).
- [ ] Labor engine: hours = base × qty × multipliers + setup/mobilization/cleanup/testing.
- [ ] Manual override with audit trail (`labor_overrides` table).
- [ ] UI: editable labor assemblies per company.

## Stage 4 — Material pricing & supplier database — P1
- [ ] `suppliers`, `material_prices` tables (supplier, sku, unit_cost, effective_date, lead_time).
- [ ] Material catalog: manufacturer, model, SKU, unit, category, waste factor.
- [ ] Price comparison by supplier; effective-date pricing (no silent price changes to approved estimates).
- [ ] Store material price snapshot on estimate line items.
- [ ] UI: material catalog management, supplier management, price updates.

## Stage 5 — Pricing & profit engine (complete) — P1
- [ ] Overhead, markup, contingency, tax, profit, gross margin (partially done in `_calc_totals`).
- [ ] Minimum project price, fixed-price vs T&M.
- [ ] Taxable/nontaxable line items.
- [ ] Subcontractor, equipment rental, permit, disposal, delivery charges.
- [ ] Show markup vs margin clearly in PDF and UI.

## Stage 6 — PDF proposals & estimate lifecycle — P1
- [ ] Professional AMY Electric template: logo, license, contact, scope, exclusions, assumptions, totals, payment schedule, acceptance/signature, expiration.
- [ ] Estimate revisions with versioning + revision log.
- [ ] Email delivery (SMTP already wired; needs config).
- [ ] Convert approved estimate → work order.
- [ ] Store PDF path and version.

## Stage 7 — Commercial module — P2
- [ ] 3-phase 120/208V and 277/480V, distribution panels, feeders, transformers, motor circuits (430), HVAC (440), demand control.
- [ ] Commercial load calculations (220 Part IV optional, demand factors).

## Stage 8 — Residential module (complete) — P2
- [ ] Full dwelling unit load calc (already standard/optional), multi-family 220.84, ADU/duplex.
- [ ] Lighting, receptacles, small appliance, laundry, ranges, dryers, HVAC.

## Stage 9 — CRM & project management — P2
- [x] Customer DB, estimate status pipeline, follow-ups, activity log (done).
- [ ] Lead pipeline, job scheduling, material purchasing list.
- [ ] Actual labor/material cost tracking vs estimated.
- [ ] Estimated vs actual profit report.
- [ ] Job photos/attachments.

## Stage 10 — AI drawing & scope analysis — P3
- [ ] PDF upload, page render, vision LLM extraction of panels/circuits/devices/distances.
- [ ] Preliminary takeoff + labor + scope generation; electrician approval gate.
- [ ] Code issue flagging vs NEC rules DB.

## Stage 11 — Roles & permissions — P2
- [ ] `role` on User (admin/estimator/viewer); permission deps; audit of who changed what.

## Stage 12 — Audit trail & calculation records — P1 (mostly done)
- [x] `calculation_records` with inputs/outputs/edition/version.
- [ ] Code warnings table; manual override audit log; never silently change approved estimates when prices/rules update.

## Stage 13 — Testing
- [ ] Unit tests for every calc (ampacity, conduit fill, box fill, voltage drop, continuous loads, grounding, service/feeder).
- [ ] Integration tests for EV charger and 200A service acceptance.
- [ ] Frontend E2E for full estimate flow.
- [ ] Per-edition test suites.

## Stage 14 — Deployment
- [ ] Docker compose with Postgres, env docs, migrations, seed scripts, CI (already partial).
- [ ] API documentation (OpenAPI already auto).

## Definition of done (first milestone)
EV charger (48A, 80ft, EMT) and 200A service upgrade produce: service load calc, panel capacity check, conductor/breaker/conduit sizing, voltage drop, grounding, full BOM, labor hours/cost, total cost, selling price, NEC refs + warnings, and a professional PDF — with traceable calculation records and electrician review gate.