import html
import json
import re
import streamlit as st
from google import genai

st.set_page_config(page_title="PrepPilot", page_icon="🚀", layout="wide")

MODEL = "gemini-2.0-flash"

VERDICT = {
    "do_fully":  {"label": "DO FULLY",  "color": "#059669", "bg": "#ECFDF5"},
    "satisfice": {"label": "SATISFICE", "color": "#F59E0B", "bg": "#FFFBEB"},
    "skip":      {"label": "SKIP",      "color": "#F43F5E", "bg": "#FFF1F2"},
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap');
#MainMenu, footer {visibility: hidden;}
html, body, [class*="css"] {font-family: 'Outfit', sans-serif;}
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.stApp {background: #fffdf9;}

.pp-hero {
  background: linear-gradient(120deg, #FF5E5B 0%, #FF8C42 45%, #FFC93C 100%);
  border-radius: 24px; padding: 2.4rem 2.5rem; margin-bottom: 1.75rem;
  color: #fff; box-shadow: 0 14px 40px -12px rgba(255,94,91,.55);
  position: relative; overflow: hidden;
}
.pp-hero:after {
  content: ""; position: absolute; right: -60px; top: -60px;
  width: 240px; height: 240px; border-radius: 50%;
  background: rgba(255,255,255,.14);
}
.pp-hero h1 {
  font-size: 3.1rem; margin: 0; font-weight: 800; letter-spacing: -1.5px;
  text-shadow: 0 2px 12px rgba(0,0,0,.12);
}
.pp-hero p {margin: .5rem 0 0; font-size: 1.08rem; font-weight: 600; opacity: .95;}
.pp-hero .pp-tag {
  display: inline-block; margin-bottom: .7rem; font-size: .7rem; font-weight: 800;
  letter-spacing: .14em; padding: .3rem .75rem; border-radius: 999px;
  background: rgba(255,255,255,.22); border: 1px solid rgba(255,255,255,.35);
}

.pp-card {
  border-radius: 18px; padding: 1.25rem 1.4rem; margin-bottom: 1rem;
  background: var(--cardbg); border: 2px solid var(--accent);
  box-shadow: 0 8px 22px -14px var(--accent);
  transition: transform .15s ease, box-shadow .15s ease;
}
.pp-card:hover {transform: translateY(-3px); box-shadow: 0 16px 32px -16px var(--accent);}
.pp-card .pp-top {display:flex; justify-content:space-between; align-items:baseline; gap:1rem;}
.pp-card h3 {margin:0; font-size:1.22rem; font-weight:800; color:#1a1a2e;}
.pp-badge {
  font-size:.66rem; font-weight:800; letter-spacing:.1em;
  padding:.35rem .7rem; border-radius:999px; white-space:nowrap;
  color:#fff; background:var(--accent); box-shadow:0 3px 10px -3px var(--accent);
}
.pp-meta {font-size:.85rem; color:#6b6b80; margin:.5rem 0 .65rem; font-weight:500;}
.pp-card ul {margin:0; padding-left:1.2rem;}
.pp-card li {font-size:.92rem; color:#33334d; margin-bottom:.28rem;}

.pp-chip {
  display:inline-block; font-size:.7rem; padding:.2rem .55rem; border-radius:8px;
  background:#FFEDD5; color:#C2410C; margin-right:.3rem; font-weight:700;
}
.pp-skip {
  border-radius:14px; padding:.85rem 1.1rem; margin-bottom:.55rem;
  background:#FFF1F2; border:2px dashed #FDA4AF; font-size:.92rem; color:#9F1239;
}
.pp-empty {
  border:3px dashed #FFD9A0; border-radius:22px; padding:3.5rem 2rem;
  text-align:center; background:#FFFBF2;
}
.pp-empty h3 {color:#EA580C; margin:0 0 .5rem; font-weight:800; font-size:1.6rem;}
.pp-empty p {color:#A16207; font-weight:500;}

section[data-testid="stSidebar"] {background:#FFF8F0; border-right:2px solid #FFE4C4;}
.stButton>button, .stFormSubmitButton>button {
  border-radius:12px !important; font-weight:800 !important; border:none !important;
  background:linear-gradient(120deg,#FF5E5B,#FF8C42) !important; color:#fff !important;
  box-shadow:0 6px 18px -6px rgba(255,94,91,.6) !important;
}
.stProgress > div > div > div > div {
  background:linear-gradient(90deg,#FFC93C,#FF8C42,#FF5E5B) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pp-hero">
  <span class="pp-tag">AI PREP &amp; TRIAGE COPILOT</span>
  <h1>PrepPilot ✦</h1>
  <p>Everything else organises your time. This one understands your workload.</p>
</div>
""", unsafe_allow_html=True)

if "items" not in st.session_state:
    st.session_state["items"] = []
if "plan" not in st.session_state:
    st.session_state["plan"] = None


@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_data
def load_prompt():
    with open("prompt.txt") as f:
        return f.read()


def clean_json(text):
    text = re.sub(r"^\s*```(?:json)?\s*", "", text)
    return re.sub(r"\s*```\s*$", "", text).strip()


def validate(plan):
    if not isinstance(plan, dict) or "blocks" not in plan:
        raise ValueError("Model response had no 'blocks'.")
    plan.setdefault("skipped", [])
    plan.setdefault("note", "")
    for b in plan["blocks"]:
        for key in ("title", "start", "minutes", "verdict", "why", "how"):
            if key not in b:
                raise ValueError(f"A block is missing '{key}'.")
        if b["verdict"] not in VERDICT:
            raise ValueError(f"Illegal verdict: {b['verdict']}")
        b["minutes"] = int(b["minutes"])
    plan["total_minutes"] = sum(b["minutes"] for b in plan["blocks"])
    return plan


def get_plan(items, hours_free):
    payload = json.dumps({"hours_free": hours_free, "items": items})
    last = None
    for _ in range(2):
        try:
            resp = get_client().models.generate_content(
                model=MODEL,
                contents=payload,
                config={
                    "system_instruction": load_prompt(),
                    "temperature": 0.2,
                    "response_mime_type": "application/json",
                },
            )
            return validate(json.loads(clean_json(resp.text)))
        except Exception as e:
            last = e
    raise last


def plan_as_text(plan):
    lines = ["TONIGHT'S PLAN", ""]
    for b in plan["blocks"]:
        lines.append(f"{b['start']}  [{VERDICT[b['verdict']]['label']}]  "
                     f"{b['title']} ({b['minutes']} min)")
        lines.append(f"   Why: {b['why']}")
        for s in b["how"]:
            lines.append(f"   - {s}")
        lines.append("")
    if plan["skipped"]:
        lines.append("SKIPPED")
        for s in plan["skipped"]:
            lines.append(f"- {s['title']}: {s['why']}")
    return "\n".join(lines)


with st.sidebar:
    st.markdown("### Tonight")
    hours_free = st.number_input("Hours free", 0.5, 12.0, 3.0, 0.5)

    st.markdown("### Add work")
    with st.form("add_item", clear_on_submit=True):
        title = st.text_input("What is it?", placeholder="Corporate Strategy pre-read")
        kind = st.selectbox("Type", ["case", "quiz", "deliverable"])
        pages = st.number_input("Pages (0 if not a reading)", 0, 200, 0)
        familiarity = st.selectbox("Familiarity", ["new", "some", "strong"])
        due = st.selectbox("Due", ["class_start", "tonight", "tomorrow_6am", "this_week"])
        weight = st.selectbox("Weight", ["low", "med", "high"])
        if st.form_submit_button("Add", type="primary", use_container_width=True):
            if not title.strip():
                st.warning("Name it first.")
            else:
                st.session_state["items"].append({
                    "title": title.strip(), "type": kind,
                    "pages": int(pages) if pages > 0 else None,
                    "familiarity": familiarity, "due": due, "weight": weight,
                })

    if st.session_state["items"]:
        st.markdown(f"### {len(st.session_state['items'])} item(s)")
        for i, it in enumerate(st.session_state["items"]):
            c1, c2 = st.columns([5, 1])
            c1.markdown(
                f"**{it['title']}**  \n"
                f"<span class='pp-chip'>{it['due'].replace('_',' ')}</span>"
                f"<span class='pp-chip'>{it['familiarity']}</span>"
                f"<span class='pp-chip'>{it['weight']}</span>",
                unsafe_allow_html=True,
            )
            if c2.button("✕", key=f"rm{i}"):
                st.session_state["items"].pop(i)
                st.rerun()
        st.divider()
        if st.button("⚡ Plan my night", type="primary", use_container_width=True):
            with st.spinner("Triaging..."):
                try:
                    st.session_state["plan"] = get_plan(
                        st.session_state["items"], hours_free)
                except Exception as e:
                    st.session_state["plan"] = None
                    st.error(f"{type(e).__name__}: {e}")
    st.caption("Nothing is stored. No login, no uploads.")


plan = st.session_state["plan"]

if not plan:
    st.markdown("""
    <div class="pp-empty">
      <h3>Nothing planned yet ✦</h3>
      <p>Add tonight's work in the sidebar, then hit <b>Plan my night</b>.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    budget = hours_free * 60
    used = plan["total_minutes"]
    full = sum(1 for b in plan["blocks"] if b["verdict"] == "do_fully")
    sat = sum(1 for b in plan["blocks"] if b["verdict"] == "satisfice")

    m = st.columns(4)
    m[0].metric("Scheduled", f"{used} min")
    m[1].metric("Budget", f"{int(budget)} min", f"{int(budget - used)} min spare")
    m[2].metric("Full passes", full)
    m[3].metric("Satisficed", sat)

    st.progress(min(used / budget, 1.0) if budget else 0.0)
    if used > budget:
        st.error(f"Needs {used} min, you have {int(budget)}. Something else has to go.")
    if plan["note"]:
        st.info(plan["note"])

    st.markdown("### Tonight's plan")
    for b in plan["blocks"]:
        v = VERDICT[b["verdict"]]
        steps = "".join(f"<li>{html.escape(s)}</li>" for s in b["how"])
        st.markdown(f"""
        <div class="pp-card" style="--accent:{v['color']}; --cardbg:{v['bg']};">
          <div class="pp-top">
            <h3>{html.escape(b['title'])}</h3>
            <span class="pp-badge">{v['label']}</span>
          </div>
          <div class="pp-meta">{html.escape(b['start'])} · {b['minutes']} min · {html.escape(b['why'])}</div>
          <ul>{steps}</ul>
        </div>
        """, unsafe_allow_html=True)

    if plan["skipped"]:
        st.markdown("### Consciously skipped")
        for s in plan["skipped"]:
            st.markdown(
                f"<div class='pp-skip'><b>{html.escape(s['title'])}</b> — "
                f"{html.escape(s['why'])}</div>", unsafe_allow_html=True)

    st.download_button("Download plan", plan_as_text(plan),
                       file_name="tonights-plan.txt")
