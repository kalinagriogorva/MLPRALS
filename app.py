# app.py
import math
from typing import Dict, List, Any, Optional

import pandas as pd
import streamlit as st

st.set_page_config(page_title="MLPRALS Readiness Self-Assessment", layout="wide")

# =========================
# Purple (Fontys-ish) UI styling
# =========================
FONTYS_PURPLE = "#6A1B9A"  # nice vivid purple; adjust if you have the exact hex

st.markdown(
    f"""
    <style>
      /* Titles / headers */
      h1, h2, h3, h4 {{ color: {FONTYS_PURPLE}; }}

      /* Expander accent */
      div[data-testid="stExpander"] > details {{
        border-left: 4px solid {FONTYS_PURPLE};
        border-radius: 10px;
        padding-left: 0.5rem;
      }}

      /* Primary button */
      .stButton > button {{
        background: {FONTYS_PURPLE};
        color: white;
        border: 1px solid {FONTYS_PURPLE};
        border-radius: 10px;
        padding: 0.5rem 1rem;
      }}
      .stButton > button:hover {{
        opacity: 0.99;
        color: {FONTYS_PURPLE};
        border: 1px solid {FONTYS_PURPLE};
      }}

      /* Progress bar (more purple) */
      div[data-testid="stProgressBar"] > div > div {{
        background-color: {FONTYS_PURPLE} !important;
      }}

      /* Info / warning / success / error left accents */
      div[data-testid="stAlert"] {{
        border-left: 6px solid {FONTYS_PURPLE} !important;
      }}

      /* Metric label accent (subtle) */
      div[data-testid="stMetricLabel"] {{
        color: {FONTYS_PURPLE};
      }}

      /* Radio selection accent: make the selected label pop a bit */
      div[role="radiogroup"] label span {{
        font-weight: 500;
      }}

      /* Make st.download_button match st.button styling */
      div[data-testid="stDownloadButton"] > button {{
        background: {FONTYS_PURPLE};
        color: white;
        border: 1px solid {FONTYS_PURPLE};
        border-radius: 10px;
        padding: 0.5rem 1rem;
      }}

      div[data-testid="stDownloadButton"] > button:hover {{
        opacity: 0.99;
        color: {FONTYS_PURPLE};
        border: 1px solid {FONTYS_PURPLE};
      }}

    </style>
    """,
    unsafe_allow_html=True,
)

# =========================
# Scoring helpers
# =========================
def floor_avg(levels: List[int]) -> int:
    return int(math.floor(sum(levels) / len(levels)))

def normalize_level(level: int) -> float:
    return (level - 1) / 4.0

def overall_level_from_nmrs(nmrs: float) -> int:
    return 1 + int(math.floor(4 * nmrs + 1e-9))

def readiness_badge(level: int) -> str:
    return {1: "Very low", 2: "Low", 3: "Medium", 4: "High", 5: "Very high"}[level]

def level_label(level: int) -> str:
    return f"Level {level} - {readiness_badge(level)}"

# =========================
# Recommendations
# =========================
def action_hint(category: str, concept: str, from_level: int, to_level: int) -> str:
    generic = {
        1: "Move from ad-hoc/manual to basic documented and digital practice.",
        2: "Standardize: define ownership, rules, and a repeatable routine.",
        3: "Automate and integrate into daily workflows (dashboards, checks, stable integrations).",
        4: "Scale and embed into governance: monitoring, feedback loops, continuous improvement.",
    }

    if category.startswith("1.") and concept in ["Data Consistency & Quality", "Data Integration", "Historical Data"]:
        generic[2] = "Define data standards + validation rules; standardize identifiers, formats, and required fields."
        generic[3] = "Add automated checks (outliers/missing), centralize datasets, and stabilize integrations."

    if category.startswith("6.") and concept in ["Access Control & Authentication", "Cybersecurity Measures", "Data Protection & Privacy"]:
        generic[2] = "Implement RBAC basics + enforce MFA; document and communicate security procedures."
        generic[3] = "Add logging/audit trails, monitoring, routine vulnerability checks, and an incident response playbook."

    if category.startswith("4.") and concept in ["Process Standardization", "Performance Monitoring", "Data-Driven Decisions"]:
        generic[2] = "Write short SOPs and define KPIs; review them on a fixed cadence."
        generic[3] = "Embed dashboards/alerts into daily work; assign owners and escalation routines."

    return generic.get(from_level, f"Improve from Level {from_level} toward Level {to_level} with structured steps.")

def advanced_recommendations(
    responses: Dict[str, Dict[str, int]],
    category_levels: Dict[str, int],
    minimums: Dict[str, int],
) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}

    for cat, concepts in responses.items():
        Ri = category_levels[cat]
        target = minimums.get(cat, 3)
        gap = target - Ri

        if gap <= 0:
            out[cat] = {
                "status": f"✅ Meets minimum (current {level_label(Ri)} ≥ minimum {level_label(target)}).",
                "progress": 1.0,
                "items": [
                    "Keep this stable (don’t break what works).",
                    "Next: strengthen monitoring and write down the routine so it stays consistent.",
                ],
            }
            continue

        weakest_sorted = sorted(concepts.items(), key=lambda x: x[1])
        weakest_names = [c for c, _ in weakest_sorted[:2]]

        items: List[str] = []
        items.append(f"**Gap to minimum:** current {level_label(Ri)} → minimum {level_label(target)} (needs +{gap}).")
        items.append(f"**Start with:** {', '.join(weakest_names)} (these pull the dimension down).")

        for concept, lvl in weakest_sorted:
            if lvl >= target:
                continue
            steps = []
            for step_from in range(lvl, target):
                step_to = step_from + 1
                steps.append(f"{step_from} → {step_to}: {action_hint(cat, concept, step_from, step_to)}")
            items.append(f"**{concept} (currently Level {lvl})**\n- " + "\n- ".join(steps))

        out[cat] = {
            "status": f"⚠️ Below minimum (current {level_label(Ri)} < minimum {level_label(target)}).",
            "progress": max(0.0, min(1.0, Ri / target)) if target > 0 else 0.0,
            "items": items,
        }

    return out

# =========================
# “Help me choose” checklist → suggested level
# =========================
def suggest_level(yes1: bool, yes2: bool, yes3: bool) -> int:
    score = sum([yes1, yes2, yes3])
    if score == 0:
        return 1
    if score == 1:
        return 2
    if score == 2:
        return 3
    return 4

def maybe_level_5(real_time: bool, base: int) -> int:
    return 5 if real_time and base >= 4 else base

# =========================
# Question bank (8×5)
# =========================
QUESTION_BANK: Dict[str, List[Dict[str, Any]]] = {
    "1. Data Readiness": [
        {"concept": "Data Collection",
         "question": "What is the level of your **data collection**, considering how operational data is captured (manual vs automated) and how consistently it is recorded?",
         "levels": {
             1: "Data written down/typed manually (paper/spreadsheets) after activities; inconsistent timing/quality.",
             2: "Data entered in basic digital tools (Excel/forms), but remains manual and scattered.",
             3: "Key activities recorded via structured digital systems (apps/barcode scanners), still needs user action.",
             4: "Data captured automatically periodically from operational systems (tracking/automated workflows).",
             5: "Real-time automated data (IoT/GPS/telematics) enabling continuous ML input.",
         }},
        {"concept": "Data Storage",
         "question": "What is the level of your **data storage**, considering whether data is centralized and easy to access (vs scattered across devices/silos)?",
         "levels": {
             1: "Stored across individual devices (laptops/phones/USB).",
             2: "Shared folders without structure/control or links to core tools.",
             3: "Stored in separate systems but siloed without unified access/oversight.",
             4: "Centralized system (ERP or dedicated database).",
             5: "Scalable storage (database server / cloud storage).",
         }},
        {"concept": "Data Consistency & Quality",
         "question": "What is the level of your **data quality**, considering missing values, errors, standard definitions, and whether validation checks exist?",
         "levels": {
             1: "Inconsistent recording; frequent errors.",
             2: "General standards exist but lack validation rules.",
             3: "Automated validation rules (duplicates/missing alerts).",
             4: "Automated processing (outliers/missing handling) ensures high integrity.",
             5: "AI-driven validation continuously corrects anomalies in real time.",
         }},
        {"concept": "Data Integration",
         "question": "What is the level of your **data integration**, considering whether systems exchange data smoothly or require manual exports/merging?",
         "levels": {
             1: "Siloed across systems; manual transfers required.",
             2: "Transfers possible but integration unstable.",
             3: "Merged for analytics (manual organization needed).",
             4: "Smooth automated integration between systems.",
             5: "Integrated data used for real-time ML-driven decisions.",
         }},
        {"concept": "Historical Data",
         "question": "What is the level of your **historical data availability**, considering how much history you keep and whether it is clean and usable for analysis?",
         "levels": {
             1: "Frequently lost/overwritten/inaccessible.",
             2: "Stored separately from active datasets.",
             3: "Structured for review and basic analysis.",
             4: "Clean/consistent format enabling deeper insights (KPIs).",
             5: "Continuously used for ML retraining and improvement.",
         }},
    ],

    "2. System & IT Maturity": [
        {"concept": "Computational Readiness",
         "question": "What is the level of your **computing capacity**, considering whether your infrastructure can support analytics/ML workloads (even small pilots)?",
         "levels": {
             1: "Only basic office computing; no ability/awareness to run ML tools.",
             2: "General resources support daily operations but not aligned with ML needs.",
             3: "Shared resources suitable for data prep/testing/inference; infra constraints considered.",
             4: "Hybrid/local+cloud setup matched to ML workloads; efficient allocation.",
             5: "Dynamic scheduling/orchestration across local+cloud with performance monitoring.",
         }},
        {"concept": "Logistics Software & ML Compatibility",
         "question": "How compatible are your **core systems** (ERP/WMS/TMS/BI) with ML, considering exports, APIs, and ability to integrate ML outputs back into workflows?",
         "levels": {
             1: "Standalone tools with no structured export or interoperability.",
             2: "Systems exist but exports/integration inconsistent or missing.",
             3: "Structured exports + basic APIs enable ML experimentation.",
             4: "ML outputs connected into planning/operations workflows.",
             5: "ML capabilities built into platforms with real-time interaction/learning.",
         }},
        {"concept": "IT Maintenance & Support",
         "question": "How strong is your **IT support**, considering whether maintenance is proactive and systems are stable for business-critical use?",
         "levels": {
             1: "No IT support; only ad-hoc troubleshooting.",
             2: "Basic support focused on daily operations; limited improvements.",
             3: "Dedicated support ensures stability/updates/troubleshooting.",
             4: "Proactive monitoring for uptime and optimization.",
             5: "AI-powered predictive IT maintenance and automated troubleshooting.",
         }},
        {"concept": "IT Adaptability & Future Readiness",
         "question": "How adaptable is your **IT landscape**, considering whether you plan upgrades and can evolve systems to support future ML use cases?",
         "levels": {
             1: "No plan; outdated systems; no awareness of relevant technologies.",
             2: "Some awareness but no concrete planning.",
             3: "Core systems stable; basic ML needs understood; planning started.",
             4: "Regular reviews/upgrades; scalable systems support ML deployment.",
             5: "Clear roadmap guides evolution; emerging tech monitored and adopted selectively.",
         }},
        {"concept": "Digital Connectivity & Network Maturity",
         "question": "How mature is your **network/connectivity**, considering stability, speed, uptime, and ability to reliably support cloud tools and data exchange?",
         "levels": {
             1: "No structured network; frequent issues; outdated hardware.",
             2: "Basic networks exist but frequent slowdowns/downtime.",
             3: "Stable/scalable network supports cloud services and data exchange reliably.",
             4: "High-speed network with monitoring in place.",
             5: "Optimized network dynamically prioritizes data flow for critical processes.",
         }},
    ],

    "3. Organizational & Cultural Readiness": [
        {"concept": "Leadership Buy-In",
         "question": "What is the level of **leadership support**, considering whether leadership understands ML value and actively allocates time/budget/resources?",
         "levels": {
             1: "No understanding of ML; not seen as relevant.",
             2: "Aware of ML potential but no vision/strategy.",
             3: "Supports ML adoption and allocates resources.",
             4: "Integrates ML into long-term strategy aligned to goals.",
             5: "Drives AI-first initiatives and innovation.",
         }},
        {"concept": "Workforce Digital Skills",
         "question": "What is the level of **workforce skills**, considering staff ability to work with digital tools, data, and analytics in daily operations?",
         "levels": {
             1: "Low digital literacy; manual processes.",
             2: "Some basic skills; no training for data-driven decision-making.",
             3: "Trained in digital tools; key staff understand data-driven decisions.",
             4: "Proficient in ML-assisted workflows and automation tools.",
             5: "Continuous upskilling in AI/ML applications.",
         }},
        {"concept": "Change Management",
         "question": "How ready is your organization for **change and adoption**, considering whether new tools/processes are introduced with a plan and accepted by staff?",
         "levels": {
             1: "Strong resistance to automation/AI-driven decisions.",
             2: "Some openness; no structured change plan.",
             3: "Structured plan exists for ML-supported workflows.",
             4: "ML changes embraced; continuous optimization via insights.",
             5: "Change management embedded; proactive AI innovation.",
         }},
        {"concept": "Employees’ Opinion",
         "question": "How supportive are employees toward **ML/digital transformation**, considering whether staff actively propose and help adopt improvements?",
         "levels": {
             1: "No advocacy for ML/digital transformation.",
             2: "Some interest; no initiatives.",
             3: "Employees suggest ML adoption and assist implementation.",
             4: "Employees help scale AI projects and ensure adoption.",
             5: "Employees lead internal AI innovation.",
         }},
        {"concept": "IT–Operations Collaboration",
         "question": "How strong is **IT–operations collaboration**, considering whether IT solutions are designed with real operational needs and feedback?",
         "levels": {
             1: "No collaboration; tech rarely used to optimize operations.",
             2: "Occasional interaction; no structured approach.",
             3: "Work together to ensure practical workflow fit.",
             4: "Seamless collaboration; IT solutions improve operations directly.",
             5: "Unified data-driven team; AI optimization embedded.",
         }},
    ],

    "4. Business Process Readiness": [
        {"concept": "Process Standardization",
         "question": "How standardized are your **core processes**, considering documentation (SOPs), consistency across employees, and repeatability?",
         "levels": {
             1: "Processes undocumented/inconsistent; vary by employee.",
             2: "Some documentation; still inconsistent.",
             3: "Standardized, documented, consistently followed.",
             4: "Optimized with data-driven insights and predictive analytics.",
             5: "ML dynamically adapts workflows in real time with minimal human intervention.",
         }},
        {"concept": "Operational Inefficiencies",
         "question": "How well do you **identify and reduce inefficiencies**, considering whether bottlenecks are measured, analyzed, and improved systematically?",
         "levels": {
             1: "Bottlenecks/delays/errors handled manually; no structured analysis.",
             2: "Recognized but fixed ad-hoc; no structured improvement process.",
             3: "Identified and addressed with structured workflows and metrics.",
             4: "Analytics predict inefficiencies and recommend solutions.",
             5: "AI proactively eliminates inefficiencies via automated optimization.",
         }},
        {"concept": "Automation Maturity",
         "question": "How automated are your operations, considering which tasks are **manual vs automated**, and whether automation supports decision-making?",
         "levels": {
             1: "Most tasks manual; no automation.",
             2: "Partial automation in a few tasks via basic tools.",
             3: "Core processes automated (tracking, updates, scheduling).",
             4: "AI-enhanced automation optimizes allocation/routing/resources.",
             5: "AI manages processes and adjusts operations in real time.",
         }},
        {"concept": "Data-Driven Decisions",
         "question": "How data-driven is your decision-making, considering whether people rely on **dashboards/metrics** (vs gut feeling) and use insights consistently?",
         "levels": {
             1: "Decisions based on intuition/experience, not data.",
             2: "Some data used; manual reports; inconsistent use.",
             3: "Dashboards support decisions using structured data.",
             4: "Proactive analytics inform decisions for efficiency/cost reduction.",
             5: "AI makes real-time operational adjustments for continuous improvement.",
         }},
        {"concept": "Performance Monitoring",
         "question": "How mature is your **performance monitoring**, considering whether KPIs exist, are reviewed regularly, and trigger actions when something is off?",
         "levels": {
             1: "No formal tracking of KPIs.",
             2: "Manual tracking; infrequent/inconsistent reviews.",
             3: "KPIs defined, tracked, and regularly reviewed.",
             4: "Dashboards provide real-time monitoring + automated anomaly alerts.",
             5: "AI refines metrics and optimizes performance continuously.",
         }},
    ],

    "5. Strategic Alignment": [
        {"concept": "ML Use Case Fit",
         "question": "How clear are your **ML use cases**, considering whether you know exactly where ML would create value (waste reduction, forecasting, routing, etc.)?",
         "levels": {
             1: "No understanding of ML relevance.",
             2: "Some awareness; no strategy.",
             3: "Specific use cases identified based on business needs.",
             4: "Use cases integrated into strategy with goals and KPIs.",
             5: "ML embedded into core operations driving innovation.",
         }},
        {"concept": "Competitive Benchmarking",
         "question": "How well do you **benchmark** against competitors/industry, considering whether you track digital/ML trends and use them to steer decisions?",
         "levels": {
             1: "No competitor/industry ML assessment.",
             2: "Basic trend research; no structured analysis.",
             3: "Analyzed competitor adoption; identified gaps/opportunities.",
             4: "Actively benchmarks against peers and adjusts strategy.",
             5: "Leads ML-driven innovation influencing the industry.",
         }},
        {"concept": "Financial Planning",
         "question": "How mature is your **financial planning for ML**, considering budgeting, ROI expectations, and decision rules for scaling pilots?",
         "levels": {
             1: "No ML budget or unclear feasibility.",
             2: "Understands costs but no structured plan.",
             3: "Budget defined; ROI assessed before implementation.",
             4: "Tracks financial impact of ML and adjusts investments based on performance.",
             5: "ML gains influence growth and long-term financial planning.",
         }},
        {"concept": "Sustainability Alignment",
         "question": "How aligned is ML adoption with **sustainability goals**, considering whether ML initiatives explicitly target environmental performance?",
         "levels": {
             1: "Sustainability not considered; ML only viewed for efficiency/cost.",
             2: "Sustainability acknowledged but not linked to ML.",
             3: "At least one ML use case supports environmental performance.",
             4: "Prioritizes sustainability use cases; includes indicators in pilot evaluation.",
             5: "ML embedded into sustainability strategy with clear environmental KPIs.",
         }},
        {"concept": "Customer Impact",
         "question": "How clearly do you connect ML initiatives to **customer impact**, considering service quality, lead time, availability, personalization, etc.?",
         "levels": {
             1: "No consideration of ML impact on customer experience.",
             2: "Awareness but no structured approach.",
             3: "Analyzed how ML can improve customer experience.",
             4: "ML enhancements improve satisfaction.",
             5: "ML insights used for engagement/loyalty/experience optimization.",
         }},
    ],

    "6. Security & Regulatory Compliance": [
        {"concept": "Data Protection & Privacy",
         "question": "What is the level of **data protection/privacy**, considering policies, encryption, handling of sensitive data, and privacy-by-design practices?",
         "levels": {
             1: "No policies; no encryption/access restrictions.",
             2: "Basic awareness; no structured protection; sensitive data may be mishandled.",
             3: "Policies exist; secure storage with encryption.",
             4: "Automated monitoring and data-loss prevention with alerts.",
             5: "AI-powered protection with real-time detection and automated response.",
         }},
        {"concept": "Cybersecurity Measures",
         "question": "How mature are your **cybersecurity measures**, considering prevention (firewalls), monitoring, updates, and incident handling?",
         "levels": {
             1: "No measures; vulnerable to threats.",
             2: "Basic firewall/antivirus not actively monitored/updated.",
             3: "Policies defined; protocols/firewalls/vulnerability assessments.",
             4: "Security framework with intrusion detection, endpoint security, real-time monitoring.",
             5: "Autonomous real-time detection and mitigation.",
         }},
        {"concept": "Regulatory Compliance",
         "question": "How ready are you for **compliance**, considering GDPR/data handling rules and any AI/ML governance requirements relevant to your sector?",
         "levels": {
             1: "No awareness of AI-related regulations/ethics.",
             2: "Some understanding; no compliance measures.",
             3: "Assessed requirements; aligns with legal/ethical guidelines.",
             4: "Compliance integrated into ML governance with risk mitigation.",
             5: "Proactively engages and sets best practices.",
         }},
        {"concept": "Risk Management & Security Governance",
         "question": "How mature is your **risk management**, considering audits, controls, contingency planning, and (if relevant) bias/fairness risks in ML?",
         "levels": {
             1: "No risk framework.",
             2: "Awareness but no structured governance/mitigation.",
             3: "Risk assessment, audits, and contingency plans exist.",
             4: "Governance integrated (incl. bias audits/fraud detection mechanisms).",
             5: "AI-driven governance automates risk detection and enforcement.",
         }},
        {"concept": "Access Control & Authentication",
         "question": "How strong is **access control**, considering role-based access, MFA, audit trails, and prevention of unauthorized access?",
         "levels": {
             1: "No restrictions; everyone can access/modify data.",
             2: "Some controls but inconsistent; unauthorized access possible.",
             3: "RBAC + MFA for key systems.",
             4: "Centralized identity/access management with audit logs.",
             5: "AI-driven identity management with real-time risk detection.",
         }},
    ],

    "7. External Dependencies & Ecosystem": [
        {"concept": "Vendor IT Maturity",
         "question": "How mature are your **vendors/partners**, considering whether their systems and practices can support integration and data exchange?",
         "levels": {
             1: "Partners/suppliers do not use IT solutions.",
             2: "Some use IT; no structured integration approach.",
             3: "Actively engages vendors and ensures compatibility.",
             4: "ML-powered vendor collaboration integrated into operations.",
             5: "Leads IT-driven partnerships influencing industry standards (AI adoption).",
         }},
        {"concept": "Industry Trends",
         "question": "How actively do you track and respond to **industry trends** in data/AI, considering whether it influences your roadmap and investments?",
         "levels": {
             1: "No awareness of ML trends in sector.",
             2: "Basic knowledge; not assessed for relevance.",
             3: "Investigates trends and evaluates impact on processes.",
             4: "Adapts innovations and aligns with best practices.",
             5: "Contributes to innovation and sets standards.",
         }},
        {"concept": "External Data",
         "question": "How well do you use **external data** (weather, market signals, supplier data, macro trends), and how integrated is it into your systems/models?",
         "levels": {
             1: "Does not use external data sources for decisions.",
             2: "Some data referenced manually; no structured integration.",
             3: "External sources integrated into systems.",
             4: "Models incorporate external data for predictive analytics/optimization.",
             5: "Continuously expands external data usage for broader insights.",
         }},
        {"concept": "AI Talent",
         "question": "What access do you have to **AI/ML talent**, considering internal skills, hiring ability, consultants, or partnerships?",
         "levels": {
             1: "No access to AI/ML expertise internally or externally.",
             2: "Aware but no hiring/partnership strategy.",
             3: "Access to expertise via hiring/consulting/IT-as-a-service.",
             4: "AI talent embedded and drives adoption/strategy.",
             5: "In-house expertise fosters innovation and training.",
         }},
        {"concept": "Research Partnerships",
         "question": "How strong are your **research/innovation partnerships**, considering pilots with universities, innovation programs, and co-development projects?",
         "levels": {
             1: "No collaboration with research institutions.",
             2: "Interest but no formal partnerships.",
             3: "Partnerships support ML initiatives.",
             4: "Co-develops solutions via pilots/collaborations.",
             5: "Key role in research shaping industry ML adoption.",
         }},
    ],

    "8. Scalability & Long-Term Viability": [
        {"concept": "IT Scalability",
         "question": "How scalable is your **IT infrastructure**, considering whether systems can handle growth in data volume, users, and ML workloads?",
         "levels": {
             1: "Hardware/system constraints prevent scaling.",
             2: "Some tools exist but struggles to scale with data/processing.",
             3: "Scalable infra with cloud/hybrid solutions.",
             4: "ML workloads dynamically allocated based on demand.",
             5: "Optimized infra scales in real time with logistics demands.",
         }},
        {"concept": "Infrastructure Flexibility",
         "question": "How flexible is your architecture, considering whether you can plug in new tools (APIs/integration) without breaking workflows?",
         "levels": {
             1: "Outdated/fragmented; manual/disconnected tools.",
             2: "Some upgrades but rigid and hard to integrate.",
             3: "Modular upgrades + partial integration via structured interfaces.",
             4: "Interoperable across systems/vendors; secure data exchange with partners.",
             5: "Composable architecture; plug-and-play ML modules with minimal disruption.",
         }},
        {"concept": "Cost Optimization",
         "question": "How well do you plan and control **costs for scaling**, considering cloud costs, tooling costs, and cost/benefit decision rules?",
         "levels": {
             1: "No strategy; inefficiencies create constraints.",
             2: "Aware of costs but no structured scaling plan.",
             3: "Costs assessed; cost-effective strategy supports scaling.",
             4: "Cost analysis optimizes investments balancing performance and budget.",
             5: "Cost optimization ensures efficient scaling with growth.",
         }},
        {"concept": "Model Maintenance",
         "question": "How mature is your approach to **model maintenance**, considering monitoring, retraining, versioning, and preventing performance degradation over time?",
         "levels": {
             1: "No maintenance strategy.",
             2: "Aware of retraining needs but no structured approach.",
             3: "Structured monitoring/retraining/version control.",
             4: "Models retrained using new data to prevent degradation.",
             5: "AI autonomously manages lifecycle and adapts to trends.",
         }},
        {"concept": "Project Governance",
         "question": "How mature is your **project governance**, considering ownership, decision-making, accountability, and responsible ML use?",
         "levels": {
             1: "No governance framework; higher operational/compliance risk.",
             2: "Basic policies exist but inconsistently enforced.",
             3: "Structured governance ensures compliance/security/responsible usage.",
             4: "Policies automated and updated based on changes.",
             5: "AI-driven governance proactively enforces policies across ML applications.",
         }},
    ],
}

MINIMUM_LEVELS: Dict[str, int] = {
    "1. Data Readiness": 4,
    "2. System & IT Maturity": 3,
    "3. Organizational & Cultural Readiness": 3,
    "4. Business Process Readiness": 3,
    "5. Strategic Alignment": 3,
    "6. Security & Regulatory Compliance": 3,
    "7. External Dependencies & Ecosystem": 3,
    "8. Scalability & Long-Term Viability": 3,
}

# =========================
# Header UI
# =========================
st.title("MLPRALS Readiness Self-Assessment")
st.caption("For SMEs to assess readiness for Machine Learning (ML) adoption.")

st.subheader("How this assessment works")
st.write(
    "You will answer 40 questions (8 dimensions × 5 concepts), each scored from Level 1–5.\n\n"
    "- Each dimension level is calculated by combining its 5 concepts.\n"
    "- The tool also calculates an overall score (0–1) for easy comparison.\n"
    "- You can use **Help me choose** whenever you’re unsure - it suggests a likely level.\n"
    "- Results appear only when all questions are completed, so your output is complete and consistent."
)

st.divider()

# =========================
# Step 1 — SME Eligibility (gated)
# =========================
if "eligibility_checked" not in st.session_state:
    st.session_state["eligibility_checked"] = False
if "is_sme" not in st.session_state:
    st.session_state["is_sme"] = None  # None = N/A

with st.container(border=True):
    st.subheader("Check SME eligibility (EU definition)")
    st.write("This assessment is intended for SMEs only:")
    st.write("- Employees: fewer than 250")
    st.write("- And either turnover ≤ €50m or balance sheet total ≤ €43m")

    c1, c2, c3, c4 = st.columns(4)
    employees = c1.number_input("Employees", min_value=0, step=1, value=0)
    turnover_m = c2.number_input("Turnover (€m)", min_value=0.0, step=0.1, value=0.0)
    balance_m = c3.number_input("Balance sheet (€m)", min_value=0.0, step=0.1, value=0.0)

    eligible_label = "N/A"
    if st.session_state["is_sme"] is True:
        eligible_label = "YES ✅"
    elif st.session_state["is_sme"] is False:
        eligible_label = "NO ❌"

    c4.metric("Eligible?", eligible_label)

    st.write("")
    if st.button("Check Eligibility", key="check_eligibility_btn"):
        st.session_state["eligibility_checked"] = True
        st.session_state["is_sme"] = (employees < 250) and ((turnover_m <= 50.0) or (balance_m <= 43.0))

if not st.session_state["eligibility_checked"]:
    st.info("Enter the SME details above and click **Check Eligibility** to continue.")
    st.stop()

if st.session_state["is_sme"] is False:
    st.error("Not eligible (this tool is for SMEs).")
    st.stop()

st.success("Eligible SME confirmed. You can continue with the assessment.")
st.divider()

# =========================
# Questionnaire section
# =========================
st.header("Questionnaire")

# =========================
# Progress bar
# =========================
TOTAL_QUESTIONS = sum(len(v) for v in QUESTION_BANK.values())

def count_completed() -> int:
    done = 0
    for cat, questions in QUESTION_BANK.items():
        for q in questions:
            key = f"{cat}::{q['concept']}"
            val = st.session_state.get(key, 0)
            if isinstance(val, int) and val != 0:
                done += 1
    return done

completed = count_completed()
progress = completed / TOTAL_QUESTIONS if TOTAL_QUESTIONS else 0.0

st.caption(f"Progress: **{completed}/{TOTAL_QUESTIONS}** questions completed.")
st.progress(progress)

st.divider()

# =========================
# Company info
# =========================
with st.container(border=False):
    st.subheader("Company information")
    company_name = st.text_input("Company name", value="")

st.divider()

# =========================
# Questions section
# =========================
st.subheader("Questions")
st.info("Tip: use **Help me choose** if you’re unsure which level fits best.")

LEVEL_CHOICES = [0, 1, 2, 3, 4, 5]  # 0 = empty

def format_level(x: int) -> str:
    return "— Select level —" if x == 0 else f"Level {x}"

responses_raw: Dict[str, Dict[str, Optional[int]]] = {}
missing: List[str] = []

for category, questions in QUESTION_BANK.items():
    with st.expander(category, expanded=False):
        responses_raw[category] = {}

        for q in questions:
            concept = q["concept"]
            prompt = q["question"]
            levels = q["levels"]

            st.markdown(f"### {concept}")
            st.write(prompt)

            # ✅ Level guide always visible (no dropdown)
            st.markdown("**Level guide (what each level means):**")
            for lvl in [1, 2, 3, 4, 5]:
                st.markdown(f"- **Level {lvl}:** {levels[lvl]}")

            # ✅ Help me choose as a "popup" using a popover
            pop_col1, pop_col2 = st.columns([1, 5])
            with pop_col1:
                with st.popover("Help me choose", use_container_width=True):
                    st.caption("Answer these and we will suggest a likely level. You can still choose any level you want.")
                    a = st.checkbox("We collect this information digitally (not only paper).", key=f"help::{category}::{concept}::a")
                    b = st.checkbox("It is standardized/consistent (clear rules/definitions; low variation).", key=f"help::{category}::{concept}::b")
                    c = st.checkbox("It is automated/integrated (minimal manual merging; runs routinely).", key=f"help::{category}::{concept}::c")
                    rt = st.checkbox("It works in real-time or is continuously improving (e.g., auto-retraining / live data).", key=f"help::{category}::{concept}::rt")
                    base = suggest_level(a, b, c)
                    suggested = maybe_level_5(rt, base)
                    st.success(f"Suggested level: **{suggested}** ({readiness_badge(suggested)})")

                    if st.button(f"Use suggested level {suggested}", key=f"use_suggested::{category}::{concept}"):
                        st.session_state[f"{category}::{concept}"] = suggested
                        st.info("Suggested level applied. You can close this and continue.")

            selected = st.radio(
                label="Select level",
                options=LEVEL_CHOICES,
                format_func=format_level,
                key=f"{category}::{concept}",
                horizontal=True,
            )

            if selected == 0:
                st.warning("Please insert the level in here.")
                responses_raw[category][concept] = None
            else:
                st.success(f"Selected: {level_label(selected)}")
                st.write(levels[selected])
                responses_raw[category][concept] = int(selected)

            st.divider()

for cat, concepts in responses_raw.items():
    for concept, val in concepts.items():
        if val is None:
            missing.append(f"{cat} → {concept}")

# =========================
# Results (only when complete)
# =========================
if missing:
    st.info(f"Results will appear after you fill all fields. Missing: {len(missing)}")
    with st.expander("Show missing fields"):
        for m in missing:
            st.write(f"- {m}")
    st.stop()

responses: Dict[str, Dict[str, int]] = {
    cat: {c: int(v) for c, v in concepts.items()} for cat, concepts in responses_raw.items()
}

category_levels: Dict[str, int] = {}
category_normalized: Dict[str, float] = {}

for cat, concept_levels in responses.items():
    lvls = list(concept_levels.values())
    Ri = floor_avg(lvls)
    category_levels[cat] = Ri
    category_normalized[cat] = normalize_level(Ri)

nmrs = sum(category_normalized.values()) / len(category_normalized)
overall_level = overall_level_from_nmrs(nmrs)

data_ok = category_levels.get("1. Data Readiness", 1) >= 4
all_ok = all(lvl >= 3 for lvl in category_levels.values())
ml_ready = data_ok and all_ok

meets_minimums = all(category_levels[dim] >= MINIMUM_LEVELS[dim] for dim in MINIMUM_LEVELS.keys())

st.divider()
st.subheader("Results")

r1, r2, r3, r4 = st.columns(4)
r1.metric("Overall score (0–1)", f"{nmrs:.2f}")
r2.metric("Overall readiness", level_label(overall_level))
r3.metric("ML-Ready (framework rule)", "YES ✅" if ml_ready else "NOT YET ❌")
r4.metric("Meets minimum levels", "YES ✅" if meets_minimums else "NOT YET ❌")

st.markdown("### Dimension summary")
rows = []
for dim in MINIMUM_LEVELS.keys():
    cur = category_levels[dim]
    min_lvl = MINIMUM_LEVELS[dim]
    rows.append({
        "Dimension": dim,
        "Current level": cur,
        "Minimum level": min_lvl,
        "Gap": min_lvl - cur,
        "Progress": round(min(1.0, cur / max(1, min_lvl)), 2),
    })
df = pd.DataFrame(rows)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("### Recommendations (clean cards)")
rec_map = advanced_recommendations(responses, category_levels, MINIMUM_LEVELS)

gaps = [(dim, MINIMUM_LEVELS[dim] - category_levels.get(dim, 0)) for dim in MINIMUM_LEVELS.keys()]
biggest = [g for g in sorted(gaps, key=lambda x: x[1], reverse=True) if g[1] > 0][:3]

with st.container(border=True):
    st.subheader("Where to focus first")
    if not biggest:
        st.success("All dimensions meet minimum levels. Next: choose one pilot use case and test it in a controlled way.")
    else:
        for dim, gap in biggest:
            st.write(f"- **{dim}** (needs +{gap})")

for dim in MINIMUM_LEVELS.keys():
    info = rec_map[dim]
    with st.container(border=True):
        left, right = st.columns([2, 1])
        with left:
            st.markdown(f"#### {dim}")
            st.write(info["status"])
        with right:
            st.write("Progress to minimum")
            st.progress(info.get("progress", 0.0))
        for line in info["items"]:
            st.markdown(f"- {line}")

st.markdown("### Export")
export_rows = []
for cat, concepts in responses.items():
    for concept, lvl in concepts.items():
        export_rows.append({
            "Company": company_name,
            "Dimension": cat,
            "Concept": concept,
            "Selected level": lvl,
            "Dimension level": category_levels[cat],
            "Minimum level": MINIMUM_LEVELS.get(cat, ""),
        })

export_df = pd.DataFrame(export_rows)
st.download_button(
    "Download answers as CSV",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name=f"mlprals_answers_{company_name or 'company'}.csv",
    mime="text/csv",
)
