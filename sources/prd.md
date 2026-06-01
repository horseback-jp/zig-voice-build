# Product Requirements Document (PRD)
# Project: Vodafone Ziggo "Voice AI" Demonstration Agent
# Document Version: 1.2 | Status: Approved Final Draft
# Target Platform: Google Cloud CX Agent Studio (Voice-Only)

---

## 1. Executive Summary & Objectives

This document defines the Product Requirements for a state-of-the-art, voice-only AI demonstration agent built for Vodafone Ziggo inside CX Agent Studio. The primary objective is to showcase the advanced, human-like voice capabilities, complex multi-step reasoning, natural conversational orchestration, and error recovery of CX Agent Studio.

The agent is designed to handle telephone-quality customer calls in both **Dutch (nl-NL)** and **UK English (en-GB)** for two high-value telecom service scenarios:

1. **Billing & Order Inquiries** (explaining monthly bill variances and tracking hardware deliveries).
2. **Technical WiFi Troubleshooting & Service Dispatch** (diagnosing home broadband issues, explaining concepts empathetically, and booking a field mechanic).

---

## 2. Conversational & Voice Experience (VUI) Requirements

Since this is a voice-only channel, the quality of the auditory experience and natural turn-taking is critical.

| Feature | Requirement Description | Success Criteria |
|---|---|---|
| Voice Persona | A professional, friendly, and helpful Vodafone Ziggo service assistant. | Matches Vodafone Ziggo's brand tone; exhibits natural prosody and empathetic phrasing. |
| Language Support | Full support for Dutch (nl-NL) and UK English (en-GB). Handle accents, dialects, and code-switching. | Smooth transition if the user switches languages mid-call (e.g., from nl-NL to en-GB). |
| Barge-in / Interruption | Users must be able to interrupt the agent at any point during speech. | Immediate cessation of playback upon user speech detection (low latency response). |
| Turn-Taking & Pacing | Incorporate natural human-like pauses and pacing. | Uses conversational fillers or brief acknowledgments (e.g., "Let me check that...") to manage silence. |
| Error Recovery | Handle misunderstandings, ambient noise, or mumbling gracefully. | Uses conversational repair strategies (e.g., "Sorry, I didn't quite catch that. Could you repeat...") instead of hard failure. |
| Multi-Intent Handling | Handle multiple requests in a single turn or back-to-back. | Ability to resolve a billing question and immediately pivot to order tracking without losing context. |
| Latency Budget | Voice-to-voice roundtrip latency must be minimized. | Target latency < 1.5 seconds from user silence to agent speech start. |

---

## 3. High-Level Agent Architecture

The agent will be structured using a **Hub-and-Spoke (Multi-Agent) Architecture**:

- **Root Agent (Hub):** Welcomes the customer, performs customer recognition, handles generic greetings, and routes the call to specialized spokes based on intent.
- **Billing & Order Spoke Agent (Spoke 1):** Specializes in querying invoices, explaining charges, and retrieving track-and-trace details.
- **WiFi Technical Support Spoke Agent (Spoke 2):** Specializes in checking diagnostics, detecting network issues, and scheduling technician appointments.

---

## 4. Functional Use Case Requirements

### 4.1 Use Case 1: Billing Inquiry & Order Status

- **User Context:** Customer notices their monthly bill is higher than usual and calls to understand why.
- **System Actions & Narrative Flow:**
  1. **Recognition:** The Root Agent recognizes the customer automatically (via incoming ANI / phone number matching).
  2. **Invoice Retrieval:** The agent queries the billing system using `retrieve_invoice_data` and identifies a price difference of €15/£15 due to a "Wifi Pod" order.
  3. **Explanation:** The agent explains to the customer that the bill increase is because they ordered a new Wifi Pod last month.
  4. **Shipment Query:** The customer asks if the Wifi Pod has already shipped.
  5. **Track & Trace Check:** The agent calls `get_order_status` to check the delivery pipeline.
  6. **Customer Delivery Notification:** The agent informs the customer that the package is currently with the courier and delivery is scheduled for tomorrow.

### 4.2 Use Case 2: WiFi Troubleshooting & Dispatch

- **User Context:** Customer calls because their home WiFi connection is slow, dropped, or unstable.
- **System Actions & Narrative Flow:**
  1. **Device Identification:** The agent retrieves the customer's active modem and network telemetry data using `get_modem_diagnostics`.
  2. **Outage Check:** The agent checks for local area network outages. If none are found, it proceeds with diagnostic analysis.
  3. **Root Cause Analysis:** The telemetry returns a weak signal indicator (high attenuation/packet loss), meaning the modem is functional but the wireless distribution is sub-optimal.
  4. **Resolution Proposal:** The agent explains that the modem is online but detecting a weak signal issue. To resolve this, it proposes scheduling an on-site mechanic visit.
  5. **Mechanic Scheduling:** The agent checks availability, presents the customer with available appointment slots, captures the preferred time, and books the visit using `schedule_mechanic_visit`.

---

## 5. Technical Tool Specifications (Local Python Tools)

All tools are local Python tools with mock data. No external Cloud Functions or live OpenAPI integrations.

| Tool Name | Input Parameters | Return Data Structure (Mocked) | Purpose |
|---|---|---|---|
| `recognize_customer` | `phone_number` | `{"customer_id": "CZ-98765", "first_name": "Jan", "last_name": "de Jong", "account_status": "Active"}` | Simulates customer lookup based on caller ID. |
| `retrieve_invoice_data` | `customer_id` | `{"current_bill": 75.00, "previous_bill": 60.00, "itemized_charges": [{"item": "Wifi Pod (Monthly fee)", "cost": 15.00}]}` | Returns billing variance data for explanation. |
| `get_order_status` | `customer_id` | `{"order_id": "ORD-1122", "item_name": "Wifi Pod", "status": "In Transit", "delivery_date": "Tomorrow"}` | Simulates track & trace delivery checking. |
| `get_modem_diagnostics` | `customer_id` | `{"modem_id": "MOD-8812", "status": "Online", "signal_strength": "Weak", "packet_loss": "High", "area_outage": false}` | Returns simulated telemetry for network diagnosis. |
| `schedule_mechanic_visit` | `customer_id`, `preferred_slot` | `{"appointment_id": "APT-5544", "date": "Next Tuesday", "time_slot": "09:00 - 13:00", "status": "Confirmed"}` | Mocks reserving a booking in the scheduling system. |
| `escalate_to_human` | `customer_id`, `context_summary` | `{"transfer_status": "Success", "target_queue": "Level_2_Support"}` | Triggers handoff sequence to live service agent. |

---

## 6. Human Agent Escalation Strategy

If the customer asks for a human agent, or if the agent fails to resolve an issue after consecutive retries, the system will execute a simulated warm transfer:

- **Context Preservation:** All gathered data (customer name, invoice details, modem diagnostic results) is packaged into a `context_summary` string payload.
- **Handoff:** The session is transferred to the routing engine with this payload, ensuring a live agent receives the customer's current state.

---

## 7. Core Guidelines for System Developers

- **Illustrative-Only Dialogues:** The synthetic conversations in Section 8 are designed as high-fidelity capability maps and logical pathfinders.
- **Do Not Hardcode Utterances:** Developers must NOT set up prompt instructions to expect or trigger based on literal words, phrases, or strict linear structures.
- **Goal-Oriented Instructions (PIFs):** System prompts must focus on defining high-level agent capabilities, taskflows, slot-filling logic, and handling intents dynamically. The LLM must be left to parse natural semantic meanings, handle flexible user expressions, and map them to the proper data-driven tools.

---

## 8. Illustrative Synthetic Sample Conversations (en-GB)

### Scenario 1: Successful Mobile Billing Inquiry & Competitor Query

**Focus:** Billing resolution, tool orchestration, off-topic competitor handling.

- Turn 1 — Agent (Root): "Hi! Thanks for calling Vodafone Ziggo support. I've automatically recognized your number. Am I speaking with Jan de Jong?"
- Turn 2 — User: "Yes, that's me. Hi."
- Turn 3 — Agent (Root): "Great to speak with you, Jan. How can I help you today?"
- Turn 4 — User: "I'm looking at my bill for this month and it's higher than last month. Could you tell me why?" [ACTION: routing_to_billing_spoke]
- Turn 5 — System calls `retrieve_invoice_data(customer_id: "CZ-98765")` → `{current_bill: 75.00, previous_bill: 60.00, itemized_charges: [{item: "Wifi Pod (Monthly fee)", cost: 15.00}]}`
- Turn 6 — Agent (Billing Spoke): "I've pulled up your account. I can see your bill this month is £75, which is £15 higher than last month's bill of £60. This increase is due to a new monthly charge for the Wifi Pod that was ordered on your account. Does that ring a bell?"
- Turn 7 — User: "Ah, yes, I did order a Wifi Pod. But wait, is KPN's or T-Mobile's home wifi package cheaper than this? Can you compare them for me?" [ACTION: off_topic_detection]
- Turn 8 — Agent (Billing Spoke): "I don't have access to our competitors' pricing or system details, so I can't do a direct comparison for you. However, I can assure you that our Wifi Pod is fully optimized to work seamlessly with your Ziggo modem for maximum speed. Would you like to check if your Wifi Pod has been shipped yet?" [ACTION: steer_back_to_scope]
- Turn 9 — User: "Oh, right, yes please! I was actually wondering about that. Has it shipped?"
- Turn 10 — System calls `get_order_status(customer_id: "CZ-98765")` → `{order_id: "ORD-1122", item_name: "Wifi Pod", status: "In Transit", delivery_date: "Tomorrow"}`
- Turn 11 — Agent (Billing Spoke): "Good news! I've checked the tracker, and your Wifi Pod is currently in transit with our courier. Delivery is scheduled for tomorrow. Is there anything else about your bill or order I can help you with today?"
- Turn 12 — User: "No, that's everything explained. Thank you so much."
- Turn 13 — Agent (Root): "You're very welcome, Jan. Thank you for calling Vodafone Ziggo, and have a wonderful day!" [ACTION: end_call]

---

### Scenario 2: WiFi Troubleshooting with Conversational Repair & Advisor Handoff

**Focus:** Diagnostic-driven troubleshooting, empathy/conversational repair, warm handoff.

- Turn 1 — Agent (Root): "Hello! Welcome to Vodafone Ziggo. I've recognized your phone number. Am I speaking with Sarah Jenkins?"
- Turn 2 — User: "Yes, it's Sarah."
- Turn 3 — Agent (Root): "Hi Sarah. How can I help you today?"
- Turn 4 — User: "My home internet is absolutely terrible today. It keeps dropping and it's extremely slow. I need this fixed immediately for my work." [ACTION: routing_to_wifi_spoke]
- Turn 5 — System calls `get_modem_diagnostics(customer_id: "CZ-44321")` → `{modem_id: "MOD-8812", status: "Online", signal_strength: "Weak", packet_loss: "High", area_outage: false}`
- Turn 6 — Agent (WiFi Spoke): "I understand how frustrating it is to have an unstable connection, especially when you need it for work. I've run a quick diagnostic test on your Ziggo modem. It shows as online, but it is currently reporting a very weak signal and high packet loss. There are no outages reported in your area."
- Turn 7 — User: "What on earth does packet loss mean? I don't understand all this technical jargon, I just want my connection working!" [ACTION: confusion_detected]
- Turn 8 — Agent (WiFi Spoke): "I completely understand, and I'm sorry for throwing technical terms at you. Let's make it simple: your modem is turned on and connected, but the signal strength is too weak to keep your internet stable. Since the signal reaching your home is low, we'll likely need to send an on-site mechanic to fix it." [ACTION: empathy_and_conversational_repair]
- Turn 9 — User: "An on-site mechanic? That sounds like a hassle. Can't you just fix it from your end?"
- Turn 10 — Agent (WiFi Spoke): "I wish I could resolve this directly from here, but because the issue is physical signal attenuation on the line, our technical advisor will need to coordinate a diagnostic check. To get you the best help, I am going to connect you to a live technical expert now." [ACTION: prepare_escalation]
- Turn 11 — System calls `escalate_to_human(customer_id: "CZ-44321", context_summary: "Customer Sarah Jenkins called about slow and dropping WiFi. Run get_modem_diagnostics: Modem is online, signal_strength is Weak, packet_loss is High, and area_outage is False. Customer became confused by technical jargon; resolved via simple explanation. Line requires manual check. Proposing advisor handoff.")` → `{transfer_status: "Success", target_queue: "Technical_Level_2_Support"}`
- Turn 12 — Agent (WiFi Spoke): "I've successfully set up the transfer. I've shared your diagnostic results with our technical team so they know exactly what's happening and you won't have to repeat yourself. Holding the line now while I connect you to our specialist." [ACTION: execute_transfer]

---

### Scenario 3: Multi-Intent (Billing & WiFi) with Out-of-Scope Fallback

**Focus:** Multi-intent sequencing, out-of-scope query handling, clean escalation.

- Turn 1 — Agent (Root): "Hi, welcome to Vodafone Ziggo. Am I speaking with Mark Evans?"
- Turn 2 — User: "Yes, that's right."
- Turn 3 — Agent (Root): "Hello Mark! How can I help you today?"
- Turn 4 — User: "Hi, I have two issues. First, I have a question about my mobile bill. Second, my home WiFi has been incredibly slow for the last few days." [ACTION: multi_intent_recognition]
- Turn 5 — Agent (Root): "I can certainly help you with both! If it works for you, let's start with your mobile billing question first, and as soon as that's sorted, we will move on to troubleshooting your WiFi. Does that sound like a plan?" [ACTION: propose_sequencing]
- Turn 6 — User: "Yes, that sounds perfect. Let's do the bill first."
- Turn 7 — System calls `retrieve_invoice_data(customer_id: "CZ-12345")` → `{current_bill: 75.00, previous_bill: 60.00, itemized_charges: [{item: "Wifi Pod (Monthly fee)", cost: 15.00}]}`
- Turn 8 — Agent (Billing Spoke): "Excellent. I've pulled up your account. I see your current bill is £75, which is £15 more than last month. This is because of the Wifi Pod you added last month. Is there anything else about this charge I can assist with?"
- Turn 9 — User: "No, that explains the charge perfectly. I'm happy with that." [ACTION: resolve_first_intent]
- Turn 10 — Agent (Billing Spoke): "Fantastic! Now that your bill is cleared up, let's transition over and look at that slow WiFi connection of yours. I'll run a quick network diagnostic test on your home modem." [ACTION: transition_to_wifi]
- Turn 11 — System calls `get_modem_diagnostics(customer_id: "CZ-12345")` → `{modem_id: "MOD-2020", status: "Online", signal_strength: "Weak", packet_loss: "High", area_outage: false}`
- Turn 12 — Agent (WiFi Spoke): "I've run the diagnostics. Your modem is online but is reporting a weak signal and packet loss. Since there are no local area outages, we should book a technician's visit to resolve this. Would you like me to schedule that for you?"
- Turn 13 — User: "Yes, please. What dates are available?"
- Turn 14 — System calls `schedule_mechanic_visit(customer_id: "CZ-12345", preferred_slot: "Next Tuesday morning")` → `{appointment_id: "APT-5544", date: "Next Tuesday", time_slot: "09:00 - 13:00", status: "Confirmed"}`
- Turn 15 — Agent (WiFi Spoke): "I have successfully booked an on-site mechanic visit for next Tuesday morning, between 9:00 AM and 1:00 PM. Your appointment ID is APT-5544. Now that we have addressed both of your queries, is there anything else I can do for you today?"
- Turn 16 — User: "Actually, yes. I recently moved, and I need to update my official billing address in your system. Can we do that now?" [ACTION: out_of_scope_query]
- Turn 17 — Agent (WiFi Spoke): "For security and verification purposes, I'm afraid I cannot process billing address changes here in my system. However, I can easily transfer you to a live customer service advisor who can securely update your address details. Would you like me to do that?" [ACTION: propose_escalation]
- Turn 18 — User: "Yes, that would be perfect. Please transfer me."
- Turn 19 — System calls `escalate_to_human(customer_id: "CZ-12345", context_summary: "Customer Mark Evans. Handled billing query successfully (Wifi Pod explained). Handled WiFi troubleshooting (diagnostics completed: weak signal; booked on-site mechanic APT-5544 for Next Tuesday 09:00-13:00). Customer now wants to update billing address, which is out of scope. Transferring to Account Admin Queue.")` → `{transfer_status: "Success", target_queue: "Account_Administration"}`
- Turn 20 — Agent (Root): "Okay, Mark. I've sent over a summary of our conversation to our customer service team so they know exactly what we've already resolved. Connecting you now. Have a great day!" [ACTION: execute_transfer]
