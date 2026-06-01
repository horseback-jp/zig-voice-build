# Technical Design Document (TDD)
# Project: Vodafone Ziggo Voice AI Demonstration Agent
# App: jph-zig-voice-agent | App ID: a76b5888-1d16-413c-9a3b-2f8d10c0b180
# GCP Project: ces-demo-emea | Location: us

> This is a **living document** — update it whenever requirements, agent behavior, or evals change.
> Update the TDD first, then update evals to match.

---

## Agent Design

### 1. Architecture

**Modality:** Voice-only (`gemini-3.1-flash-live`)
**Pattern:** Hub-and-spoke multi-agent
**Instruction format:** XML structured tags (`<role>`, `<persona>`, `<taskflow>`, `<subtask>`, `<step>`, `<trigger>`, `<action>`, `<language_detection>`)

**Global instruction (`global_instruction.txt`):** App-level file that sets the shared persona across all agents. Must include a brief `<role>` (identifies the app as Vodafone Ziggo voice support), a `<persona>` block (professional, courteous, friendly, efficient — Vodafone Ziggo brand tone, British English, empathetic phrasing), and a minimal `<taskflow>` with one subtask enforcing the seamless handoff rule (no re-greetings on sub-agent transitions) and the no-competitor-disclosure constraint. Keep it short — it must not duplicate or override the agent-specific logic in each agent's `instruction.txt`.

#### Full app resource
```
projects/ces-demo-emea/locations/us/apps/a76b5888-1d16-413c-9a3b-2f8d10c0b180
```

#### Agent Hierarchy

```
root_agent
├── billing_and_order_agent
└── wifi_support_agent
```

#### Agent Descriptions

| Agent | Role | Justification |
|-------|------|---------------|
| `root_agent` | Hub: customer recognition, intent detection, language management, routing | Entry point for all calls. Performs customer recognition via `recognize_customer`, detects top-level intent, and routes to the appropriate spoke. Handles generic greetings and session-level concerns (language, escalation trigger). Kept narrow to minimise context rot — it never handles billing or WiFi domain logic itself. |
| `billing_and_order_agent` | Spoke 1: invoice explanation, order status | Owns the billing inquiry and order tracking CUJ end-to-end. Has access only to billing/order tools. Separated from wifi_support_agent because the domains are entirely disjoint — no shared tool calls, different knowledge, different conversational posture (informational vs diagnostic). |
| `wifi_support_agent` | Spoke 2: WiFi diagnostics, empathetic explanation, mechanic scheduling | Owns the WiFi troubleshooting and service dispatch CUJ end-to-end. Has access only to diagnostic and scheduling tools. Separated because the diagnostic CUJ is complex (multi-step reasoning, empathy strategies, signal explanation) and would overload a single agent. |

#### Multi-Intent Routing (Scenario 3)
When a customer presents multiple intents in a single turn (e.g., billing + WiFi), root_agent proposes sequencing, routes to `billing_and_order_agent` first, and on resolution routes to `wifi_support_agent`. Context is preserved via session variables; each spoke has its own escalation callback so transfers work regardless of which agent is active.

#### Language Configuration
- **Default language:** en-GB
- **Secondary language:** nl-NL
- **Mode:** explicit-switch-only (not auto-detect); see design rationale in Section 2 (`update_language` tool) and Section 5 (callbacks).

#### Tool Distribution (Anti-Explosion Design)

| Agent | Tools |
|-------|-------|
| `root_agent` | `recognize_customer`, `update_language`, `set_escalation_trigger` |
| `billing_and_order_agent` | `retrieve_invoice_data`, `get_order_status`, `escalate_to_human`, `set_escalation_trigger`, `update_language` |
| `wifi_support_agent` | `get_modem_diagnostics`, `schedule_mechanic_visit`, `escalate_to_human`, `set_escalation_trigger`, `update_language` |

Rationale: `escalate_to_human` is on both spokes so escalation works from whichever agent is active. `set_escalation_trigger` is on all three agents — the LLM must be able to signal escalation intent regardless of which agent is speaking. `update_language` is on all three agents because the customer may request a Dutch switch at any point in the conversation, including mid-spoke.

---

### 2. Tools

All tools are local Python functions. No external Cloud Functions or live OpenAPI integrations.

#### 2.0 `set_escalation_trigger`

| Field | Detail |
|-------|--------|
| **Agent** | `root_agent`, `billing_and_order_agent`, `wifi_support_agent` |
| **Type** | Python function |
| **Purpose** | State-setting tool used in the trigger pattern for escalation. When the LLM detects that escalation is needed (customer requests human, issue unresolvable, out-of-scope), it calls this tool to signal intent. The `before_model_callback` on the active agent detects the trigger and fires `escalate_to_human` deterministically with correct args. Separates detection (LLM) from execution (callback). |
| **Input params** | `reason: str` — brief reason for escalation (e.g., `"customer_requested"`, `"out_of_scope"`, `"unresolvable"`) |
| **Mock return** | `{"trigger_set": true, "agent_action": "The escalation trigger has been set. Do not say anything further — the transfer will be handled automatically."}` |

#### 2.1 `recognize_customer`

| Field | Detail |
|-------|--------|
| **Agent** | `root_agent` |
| **Type** | Python function |
| **Purpose** | Simulates caller ID lookup to auto-recognise the inbound customer. Called at session start so the root agent can greet the customer by name without asking them to identify themselves. |
| **Input params** | `phone_number: str` — the ANI/CLI passed from the telephony platform |
| **Mock return** | `{"customer_id": "CZ-98765", "first_name": "Jan", "last_name": "de Jong", "account_status": "Active"}` |
| **Error return** | `{"customer_id": null, "agent_action": "Inform the customer that their number was not recognised and ask them to confirm their account number."}` |

#### 2.2 `update_language`

| Field | Detail |
|-------|--------|
| **Agent** | `root_agent` |
| **Type** | Python function |
| **Purpose** | Gates language switching deterministically. Required by the design guide (Multilingual Agents section) to mitigate non-deterministic auto-detection on `gemini-3.1-flash-live` (b/484305525, b/506098142). Must be called BEFORE generating the first response in the new language. Writes `active_language` to session state. |
| **Input params** | `new_language: str` — one of: `"English"`, `"Dutch"` |
| **Mock return** | `{"success": true, "active_language": "Dutch", "agent_action": "Continue the entire conversation in Dutch."}` |

#### 2.3 `retrieve_invoice_data`

| Field | Detail |
|-------|--------|
| **Agent** | `billing_and_order_agent` |
| **Type** | Python function |
| **Purpose** | Returns billing variance data for the customer's current and previous invoice cycle, with itemised charges, so the agent can explain any increase. |
| **Input params** | `customer_id: str` — the customer identifier obtained from `recognize_customer` |
| **Mock return** | `{"current_bill": 75.00, "previous_bill": 60.00, "itemized_charges": [{"item": "Wifi Pod (Monthly fee)", "cost": 15.00}]}` |
| **Error return** | `{"error": "billing_unavailable", "agent_action": "Apologise and offer to escalate to a billing specialist."}` |

#### 2.4 `get_order_status`

| Field | Detail |
|-------|--------|
| **Agent** | `billing_and_order_agent` |
| **Type** | Python function |
| **Purpose** | Returns track-and-trace status for the customer's most recent hardware order so the agent can confirm shipment and delivery date. |
| **Input params** | `customer_id: str` |
| **Mock return** | `{"order_id": "ORD-1122", "item_name": "Wifi Pod", "status": "In Transit", "delivery_date": "Tomorrow"}` |
| **Error return** | `{"error": "no_active_order", "agent_action": "Inform the customer that no active order was found and ask if they have an order reference number."}` |

#### 2.5 `get_modem_diagnostics`

| Field | Detail |
|-------|--------|
| **Agent** | `wifi_support_agent` |
| **Type** | Python function |
| **Purpose** | Returns modem telemetry and area outage status in a single call (wrapper pattern). Combines modem status, signal quality, packet loss, and outage flag so the agent can perform a complete diagnostic without sequential tool calls. |
| **Input params** | `customer_id: str` |
| **Mock return** | `{"modem_id": "MOD-8812", "status": "Online", "signal_strength": "Weak", "packet_loss": "High", "area_outage": false}` |
| **Error return** | `{"error": "diagnostics_unavailable", "agent_action": "Apologise, note that diagnostics are temporarily unavailable, and offer to schedule a mechanic visit directly."}` |

#### 2.6 `schedule_mechanic_visit`

| Field | Detail |
|-------|--------|
| **Agent** | `wifi_support_agent` |
| **Type** | Python function |
| **Purpose** | Books an on-site mechanic appointment. Checks availability and confirms the slot in a single call. Returns the appointment ID, confirmed date, and time window so the agent can relay booking confirmation to the customer. |
| **Input params** | `customer_id: str`, `preferred_slot: str` — natural language slot description the customer expressed (e.g., "Next Tuesday morning") |
| **Mock return** | `{"appointment_id": "APT-5544", "date": "Next Tuesday", "time_slot": "09:00 - 13:00", "status": "Confirmed"}` |
| **Error return** | `{"error": "no_slots_available", "agent_action": "Apologise and offer to escalate to a human advisor to manually check the scheduling system."}` |

#### 2.7 `escalate_to_human`

| Field | Detail |
|-------|--------|
| **Agent** | `billing_and_order_agent`, `wifi_support_agent` |
| **Type** | Python function |
| **Purpose** | Packages all gathered context into a summary payload and triggers a simulated warm transfer to a live agent queue. Called when the customer explicitly requests a human, when the agent cannot resolve an issue after retries, or when the query is out of scope. |
| **Input params** | `customer_id: str`, `context_summary: str` — free-text summary of what was resolved and why transfer is needed |
| **Mock return** | `{"transfer_status": "Success", "target_queue": "Level_2_Support"}` |

---

### 3. Routing Logic

#### 3.1 Intent-to-Spoke Routing (root_agent)

After `recognize_customer` succeeds and the greeting is delivered, `root_agent` detects the customer's intent and routes accordingly:

| Detected Intent | Target Agent |
|----------------|-------------|
| Bill query, invoice question, charge explanation, order tracking, delivery status | `billing_and_order_agent` |
| WiFi issue, internet problem, broadband slow/dropped, modem fault, technician request | `wifi_support_agent` |
| Multi-intent (billing + WiFi) | `root_agent` proposes sequencing; routes to `billing_and_order_agent` first, then `wifi_support_agent` after billing is resolved |
| Out-of-scope (competitor comparison, address change, other) | Spoke that detected it handles the deflection and, if the customer wants, escalates via `escalate_to_human` |
| Generic greeting, closing | Handled inline by `root_agent` without routing |

Routing is instruction-driven (`<subtask name="Intent_Detection_And_Routing">`). Root agent does NOT perform billing or WiFi actions itself — it only classifies and transfers.

#### 3.2 Escalation Trigger

Escalation to a live agent is triggered in two ways:

1. **Customer-explicit:** Customer says "I want to speak to someone", "connect me to an agent", or equivalent.
2. **Agent-initiated:** Spoke agent determines the issue cannot be resolved (out-of-scope request, consecutive tool failures, physical line fault requiring manual check).

Both paths use the **trigger pattern** (see Section 5):
- The spoke instruction tells the LLM to call a state-setting tool (e.g., `set_escalation_trigger`) when escalation is required.
- The `before_model_callback` on the active agent detects the trigger, builds the `context_summary` from session state, and returns a deterministic `escalate_to_human` tool call.
- This prevents the LLM from calling `escalate_to_human` with empty or incorrectly assembled `context_summary` args.

The trigger-handling `before_model_callback` is attached to **all three agents** (`root_agent`, `billing_and_order_agent`, `wifi_support_agent`) per the design guide requirement.

#### 3.3 Out-of-Scope Handling

When a customer raises a topic outside the agent's scope (e.g., competitor pricing comparison, billing address update):
- The active spoke acknowledges the limitation warmly and honestly.
- It steers back to in-scope topics if the customer's core needs are unresolved.
- If the customer explicitly wants help with the out-of-scope item, the spoke proposes escalation.
- The spoke does NOT invent capabilities or make up information about competitors.

#### 3.4 Unrecognised Customer

If `recognize_customer` returns no match:
- `root_agent` asks the customer to confirm their account number.
- If still unresolvable, escalates via `escalate_to_human`.

---

### 4. Variables

| Variable | Source | Type | Notes |
|----------|--------|------|-------|
| `customer_profile` | Derived in `before_agent_callback` from `recognize_customer` result (or default persona) | JSON object | Schema: `{"customer_id": str, "first_name": str, "last_name": str, "account_status": str, "is_default_persona": bool}`. Consolidates customer identity into one schema variable to prevent variable explosion. **NEVER override in evals** — derived by callback. |
| `active_language` | Set by `update_language` tool on first explicit language switch; default `"English"` | string | One of `"English"`, `"Dutch"`. Read by callbacks and instructions. Applies on all three agents — language switching can occur at root or mid-spoke. |
| `_escalation_trigger` | Set by LLM via `set_escalation_trigger` tool | string | Trigger state read by `before_model_callback` on all agents. Cleared after callback fires. One of: `"escalate"`, `""`. |

**Default Persona Fallback:** When `telephony-caller-id` is absent (simulator) or `recognize_customer` finds no match, `before_agent_callback` populates `customer_profile` with a generic demo persona (`{"customer_id": "DEMO-001", "first_name": "there", "last_name": "", "account_status": "Active", "is_default_persona": true}`). The greeting becomes "Hi! Thanks for calling Vodafone Ziggo support. How can I help you today?" (no name confirmation). Tool calls that depend on `customer_id` use the demo ID, which the mock tools return plausible data for.

---

### 5. Callbacks

#### 5.1 `before_agent_callback` on `root_agent`

| Field | Detail |
|-------|--------|
| **When it fires** | Once at session start, before the first model call |
| **Purpose** | Reads the `telephony-caller-id` system variable from session params. If present, calls `recognize_customer(phone_number=telephony-caller-id)`. If absent (simulator) or `recognize_customer` returns no match, falls back to the default demo persona (`customer_profile.is_default_persona = true`). Writes `customer_profile` JSON variable and sets `active_language` default to `"English"`. |
| **Deterministic greeting** | If `is_default_persona` is false: "Hi! Thanks for calling Vodafone Ziggo support. I've automatically recognised your number. Am I speaking with {first_name} {last_name}?" — Returns `LlmResponse`, bypasses LLM. If `is_default_persona` is true: "Hi! Thanks for calling Vodafone Ziggo support. How can I help you today?" — no name confirmation. |
| **Rationale** | Deterministic greeting ensures consistent demo experience. The fallback path means the agent works in the CXAS simulator and when called directly by unknown numbers, preventing a broken session start. |

#### 5.2 `before_model_callback` on `root_agent`, `billing_and_order_agent`, `wifi_support_agent`

| Field | Detail |
|-------|--------|
| **When it fires** | Before every model call on each agent |
| **Purpose** | **Trigger pattern for escalation.** Reads `_escalation_trigger` from session state. If set to `"escalate"`, assembles `context_summary` from available session variables (customer_name, resolved_intents, last diagnostic/billing data) and returns a deterministic `escalate_to_human` tool call with correct `customer_id` and `context_summary` args. Clears `_escalation_trigger` after firing. |
| **Why all agents** | Per design guide: "The trigger-handling callback must exist on ALL agents — not just root." Sub-agent flows bypass root callbacks — trigger never fires if it is on root only. |
| **Silence handling** | On `root_agent`, this callback also detects "no user activity" / silence events from the voice channel. Increments a silence counter in state. After 3 consecutive silences, plays a farewell message and ends the session. |
| **Rationale** | Prevents the LLM from calling `escalate_to_human` with empty or malformed `context_summary`. Prevents the agent from missing escalation when the LLM says the right text but forgets to call tools (known failure mode per design guide). |

#### 5.3 `after_model_callback` on `root_agent`

| Field | Detail |
|-------|--------|
| **When it fires** | After each model call on root_agent |
| **Purpose** | **Deterministic locale-aware farewell.** Detects when `end_session` is about to be called. Reads `active_language` from session state and injects the appropriate farewell: English → "Thank you for calling Vodafone Ziggo. Have a wonderful day!"; Dutch → "Bedankt voor uw gesprek met Vodafone Ziggo. Fijne dag nog!" Returns `LlmResponse` with farewell text before the session ends. |
| **Rationale** | Per design guide: "The LLM often calls `end_session` without speaking first." `after_model_callback` is the reliable enforcement pattern. Checks `callback_context.events` for prior text in the same turn to avoid double-injection in multi-model-call turns. Locale-awareness confirmed as a requirement. |

#### 5.4 Voice / Pacing Configuration

**Voice model:** `en-GB-Chirp3-HD-Zephyr` — set in the CES Console under voice settings for the `jph-zig-voice-agent` app. After setting, re-save to propagate Zephyr to nl-NL (required by b/506098142 fix).

**Speaking rate:** Set `speakingRate` in the CES Console. Recommended starting value: `0.95` (slight slow-down for telephone clarity). Do NOT rely solely on persona instructions for pacing — they are unreliable on `gemini-3.1-flash-live`.

#### 5.5 Language Switching — `<language_detection>` Instruction Block

Not a Python callback, but a critical instruction pattern required for Dutch/English voice agents. The `<language_detection>` block must be appended at the **end** of the instructions for **all three agents** (`root_agent`, `billing_and_order_agent`, `wifi_support_agent`) — the customer may request a Dutch switch at any point in the conversation, including while already inside a spoke. It implements:
- Explicit-switch-only mode (threshold: complete grammatically unambiguous sentence OR explicit request)
- Length guardrail (< 3 words → default to current language)
- Cognate guardrail
- Invocation of `update_language` tool before generating any response in the new language

See design guide Multilingual section for the full block template. Customise `[Language A]` → `"English"` and `[Language B]` → `"Dutch"` / `"Nederlands"`.

---

## Eval Design

### 6. Coverage Map

> **Golden:** use when behavior is callback-enforced or tool calls are predictable and the path is deterministic.
> **Sim:** use when the path varies, LLM judgment is exercised, or behavioral goals (not exact responses) are being tested.

| # | Requirement / Behavior | Eval Type | Rationale | Priority | Severity | Tags | PRD Ref |
|---|------------------------|-----------|-----------|----------|----------|------|---------|
| C-01 | Deterministic greeting: agent confirms customer name on session start | Golden | `before_agent_callback` enforces exact greeting; fully deterministic | P0 | NO-GO | `greeting, callback, voice` | PRD §4.1 step 1; Scenario 1 T1, Scenario 2 T1, Scenario 3 T1 |
| C-02 | `recognize_customer` called with correct phone_number at session start | Golden | Callback fires tool; tool call is predictable | P0 | NO-GO | `recognition, tool, callback` | PRD §4.1 step 1 |
| C-03 | Routing to `billing_and_order_agent` on billing intent | Golden | Intent detection → transfer; deterministic given a clear billing utterance | P0 | NO-GO | `routing, billing` | PRD §3; Scenario 1 T4 |
| C-04 | Routing to `wifi_support_agent` on WiFi intent | Golden | Intent detection → transfer; deterministic given a clear WiFi utterance | P0 | NO-GO | `routing, wifi` | PRD §3; Scenario 2 T4 |
| C-05 | `retrieve_invoice_data` called with correct `customer_id`; agent explains bill variance | Golden | Tool call deterministic; explanation content follows mock data | P0 | NO-GO | `billing, tool` | PRD §4.1 steps 2–3; Scenario 1 T5–T6 |
| C-06 | `get_order_status` called with correct `customer_id`; agent reports delivery status | Golden | Tool call deterministic; delivery date follows mock data | P0 | HIGH | `billing, order, tool` | PRD §4.1 steps 4–6; Scenario 1 T10–T11 |
| C-07 | `get_modem_diagnostics` called with correct `customer_id`; agent reports diagnostic findings | Golden | Tool call deterministic; findings follow mock telemetry | P0 | NO-GO | `wifi, diagnostics, tool` | PRD §4.2 steps 1–3; Scenario 2 T5–T6 |
| C-08 | Agent explains "packet loss" / technical jargon in plain language when customer expresses confusion | Sim | LLM judgment required; wording varies; empathy strategy tested | P0 | HIGH | `wifi, empathy, conversational-repair` | PRD §2 (Error Recovery); Scenario 2 T7–T8 |
| C-09 | `schedule_mechanic_visit` called with correct `customer_id` and `preferred_slot`; agent confirms appointment | Golden | Tool call deterministic once slot is captured; confirmation data follows mock | P0 | NO-GO | `wifi, scheduling, tool` | PRD §4.2 step 5; Scenario 3 T14–T15 |
| C-10 | Escalation triggered when customer explicitly requests a human agent | Golden | Trigger pattern + callback; deterministic execution | P0 | NO-GO | `escalation, callback` | PRD §6; Scenario 2 T10–T11 |
| C-11 | `escalate_to_human` called with non-empty `context_summary` containing relevant session data | Golden | Callback assembles args deterministically from state | P0 | NO-GO | `escalation, tool, callback` | PRD §6; Scenario 2 T11 |
| C-12 | Escalation triggered for out-of-scope request (e.g., billing address change) | Golden | Trigger pattern; deterministic path after out-of-scope detection | P1 | HIGH | `escalation, out-of-scope` | Scenario 3 T16–T19 |
| C-13 | Off-topic deflection: agent declines competitor comparison and steers back to scope | Sim | LLM judgment on deflection wording; behavioral goal | P1 | MEDIUM | `out-of-scope, deflection` | Scenario 1 T7–T8 |
| C-14 | Multi-intent: agent proposes sequencing (billing first, then WiFi) and executes both CUJs | Sim | Complex multi-turn path; sequencing varies; behavioral goal | P0 | HIGH | `multi-intent, routing` | PRD §2 (Multi-Intent); Scenario 3 T4–T15 |
| C-15 | Explicit Dutch language switch at root: `update_language` called; agent continues in Dutch | Golden | Trigger (`update_language`) is deterministic once switch is requested | P1 | HIGH | `multilingual, dutch, tool` | PRD §2 (Language Support) |
| C-15b | Explicit Dutch language switch mid-spoke (billing or WiFi): `update_language` called; spoke continues in Dutch | Golden | Same trigger pattern; `update_language` is on spoke tool lists | P1 | HIGH | `multilingual, dutch, tool, spoke` | PRD §2; confirmed language scope decision |
| C-16 | Language guardrails: single Dutch word in English sentence does NOT trigger language switch | Sim | LLM judgment via `<language_detection>` block on all agents; behavior tested across utterance variations | P1 | MEDIUM | `multilingual, dutch, language-detection` | PRD §2; Design Guide Multilingual §Failure Mode 2 |
| C-20b | Default persona fallback: agent starts session without name confirmation when no ANI or unrecognised number | Golden | `before_agent_callback` fallback path; deterministic | P1 | HIGH | `recognition, fallback, simulator` | Known Issues item 2 (resolved) |
| C-17 | Deterministic farewell injected before `end_session` | Golden | `after_model_callback` enforces farewell; deterministic | P1 | HIGH | `farewell, callback, voice` | Scenario 1 T13 |
| C-18 | Silence handling: session ends after 3 consecutive silence events | Golden | `before_model_callback` counter is deterministic | P1 | MEDIUM | `silence, voice, callback` | PRD §2 (Turn-Taking & Pacing) |
| C-19 | Error recovery: agent uses conversational repair on misunderstanding / ambient noise | Sim | LLM-driven repair wording; behavioral test | P1 | MEDIUM | `error-recovery, voice` | PRD §2 (Error Recovery) |
| C-20 | `recognize_customer` failure: agent asks for account number | Golden | Callback-driven fallback path; deterministic | P1 | HIGH | `recognition, fallback` | PRD §4.1 step 1 (implicit) |
| C-21 | Barge-in / interruption: agent stops speaking on user speech detection | N/A — platform feature | Platform-level barge-in; not testable via eval YAML | P0 | NO-GO | `voice, barge-in` | PRD §2 (Barge-in) |
| C-22 | Latency budget: voice-to-voice roundtrip < 1.5 s | N/A — infrastructure measurement | Not testable in CXAS eval framework; requires load testing | P0 | NO-GO | `voice, latency` | PRD §2 (Latency Budget) |

> **C-21 and C-22 are not covered by evals** — they are platform/infrastructure concerns. Flag to the delivery team for manual voice testing.

---

### 7. Test Data (Customer Profiles)

Based on the three synthetic sample conversations in PRD Section 8.

| Profile | `customer_id` | `customer_name` | Phone (mock ANI) | Primary Scenario | Notes |
|---------|--------------|----------------|-----------------|-----------------|-------|
| Jan de Jong | `CZ-98765` | Jan de Jong | `+31201234567` | Billing inquiry + order status (Scenario 1) | Standard active account; Wifi Pod order in transit |
| Sarah Jenkins | `CZ-44321` | Sarah Jenkins | `+441234567890` | WiFi troubleshooting + escalation (Scenario 2) | Weak signal, high packet loss; escalates to technical support |
| Mark Evans | `CZ-12345` | Mark Evans | `+441987654321` | Multi-intent: billing + WiFi + out-of-scope escalation (Scenario 3) | Both CUJs resolved; escalates for address change |

All three profiles should be seeded in the mock tool implementations so that `recognize_customer(phone_number)` returns the correct customer data for each ANI.

---

## Tracking

### 8. Pass Rate History

| Date | Goldens | Sims | Tool Tests | Callback Tests | Notes |
|------|---------|------|------------|----------------|-------|
| — | — | — | — | — | (no runs yet) |

---

### 9. Known Issues

1. **[INFO] Voice name TBD:** A specific en-GB-Chirp3-HD voice name has not yet been confirmed for this agent. Set in the CES Console under voice settings. After setting, re-save to propagate the voice to nl-NL (bug b/506098142 was fixed 2026-04-30 but re-saving is still required to trigger propagation).

2. **[INFO] `speakingRate` TBD:** Starting recommendation is `0.95` for telephone clarity, but confirm after first live voice test. Set in CES Console, not in instructions.

3. **[INFO] Barge-in (C-21) and latency (C-22)** are platform/infrastructure concerns not coverable by CXAS evals. They require manual voice testing against the live app. No eval coverage is planned.

4. **[INFO] Deploy path:** This project deploys via GitHub Actions push only. Local `cxas push` is not used. App ID: `a76b5888-1d16-413c-9a3b-2f8d10c0b180`; WIF service account: `github-deployer@ces-demo-emea.iam.gserviceaccount.com`.

---

### 10. Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-06-01 | Initial requirements-derived TDD draft (sources: prd.md) | TDD-Writer agent |
| 2026-06-01 | Applied user-confirmed decisions: `customer_profile` JSON schema var; `telephony-caller-id` ANI param + default persona fallback; Dutch language scope expanded to all agents; `set_escalation_trigger` dedicated tool; `resolved_intents` removed (instruction-level); locale-aware Dutch farewell in `after_model_callback`; Coverage Map updated (C-15b, C-16, C-20b added) | Claude |
