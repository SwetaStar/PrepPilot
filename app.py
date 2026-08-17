import html
import json
import re
import streamlit as st
from google import genai

st.set_page_config(page_title="PrepPilot", page_icon="🚀", layout="wide")

MODEL = "gemini-2.0-flash"

VERDICT = {
    "do_fully":  {"label": "DO FULLY",  "color": "#15803d", "bg": "#f0fdf4"},
    "satisfice": {"label": "SATISFICE", "color": "#b45309", "bg": "#fffbeb"},
    "skip":      {"label": "SKIP",      "color": "#b91c1c", "bg": "#fef2f2"},
}

st.markdown("""
<style>
#MainMenu, footer {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1200px;}
.pp-hero {
  background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 60%, #6d28d9 100%);
  border-radius: 18px; padding: 2rem 2.25rem; margin-bottom: 1.75rem; color: #fff;
}
.pp-hero h1 {font-size: 2.6rem; margin: 0; font-weight: 800; letter-spacing: -1px;}
.pp-hero p {margin: .4rem 0 0; opacity: .82; font-size: 1.02rem;}
.pp-card {
  border-radius: 14px; padding: 1.1rem 1.3rem; margin-bottom: .85rem;
  border: 1px solid #e5e7eb; border-left: 6px solid var(--accent);
  background: var(--cardbg);
}
.pp-card .pp-top {display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;}
.pp-card h3 {margin: 0; font-size: 1.15rem; font-weight: 700; color: #111827;}
.pp-badge {
  font-size: .68rem; font-weight: 800; letter-spacing: .09em;
  padding: .3rem .6rem; border-radius: 999px; white-space: nowrap;
  color: #fff; background: var(--accent);
}
.pp-meta {font-size: .82rem; color: #6b7280; margin: .45rem 0 .6rem;}
.pp-card ul {margin: 0; padding-left: 1.15rem;}
.pp-card li {font-size: .9rem; color: #374151; margin-bottom: .22rem;}
.pp-chip {
  display: inline-block; font-size: .72rem; padding: .18rem .5rem;
  border-radius: 6px; background: #eef2ff; color: #4338ca;
  margin-right: .3rem; font-weight: 600;
}
.pp-skip {
  border-radius: 10px; padding: .75rem 1rem; margin-bottom: .5rem;
  background: #fef2f2; border: 1px dashed #fca5a5; font-size: .9rem; color: #7f1d1d;
}
.pp-empty {
  border: 2px dashed #d1d5db; border-radius: 16px; padding: 3rem 2rem;
  text-align: center; color: #9ca3af;
}
.pp-empty h3 {color: #6b7280; margin: 0 0 .4rem; font-weight: 700;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="pp-hero">
  <h1>PrepPilot</h1>
  <p>Existing tools organise your time. This one understands your workload.</p>
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


# ---------------- sidebar: input ----------------
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
                f"**{it['title']}**  \n<span class='pp-chip'>{it['due'].replace('_',' ')}</span>"
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


# ---------------- main: output ----------------
plan = st.session_state["plan"]

if not plan:
    st.markdown("""
    <div class="pp-empty">
      <h3>No plan yet</h3>
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
