import json
import re
import streamlit as st
from google import genai

st.set_page_config(page_title="PrepPilot", page_icon="🚀")
st.title("PrepPilot")
st.caption("Tell me tonight's workload. I'll tell you what to do, skim, and skip.")

MODEL = "gemini-2.0-flash"

VERDICT = {
    "do_fully": ("🟢", "DO FULLY"),
    "satisfice": ("🟡", "SATISFICE"),
    "skip": ("🔴", "SKIP"),
}

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
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def validate(plan):
    if not isinstance(plan, dict):
        raise ValueError("Model did not return an object.")
    if "blocks" not in plan:
        raise ValueError("Response has no 'blocks'.")
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
    last_error = None
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
            last_error = e
    raise last_error


def render_plan(plan, budget_minutes):
    used = sum(b["minutes"] for b in plan["blocks"])
    st.header("Tonight's plan")
    if used > budget_minutes:
        st.warning(
            f"This plan needs {used} min but you only have {int(budget_minutes)}. "
            "Something else has to go."
        )
    st.progress(
        min(used / budget_minutes, 1.0) if budget_minutes else 0.0,
        text=f"{used} of {int(budget_minutes)} minutes used",
    )
    if plan.get("note"):
        st.info(plan["note"])

    for b in plan["blocks"]:
        icon, label = VERDICT.get(b["verdict"], ("⚪", b["verdict"].upper()))
        with st.container(border=True):
            top = st.columns([6, 2])
            top[0].markdown(f"### {b['title']}")
            top[1].markdown(f"### {icon} {label}")
            st.caption(f"{b['start']} · {b['minutes']} min · {b['why']}")
            for step in b["how"]:
                st.markdown(f"- {step}")

    if plan.get("skipped"):
        st.subheader("Consciously skipped")
        for s in plan["skipped"]:
            st.markdown(f"🔴 **{s['title']}** — {s['why']}")

    st.caption("Nothing you enter is stored. No login, no uploads, no saved data.")


hours_free = st.number_input(
    "Hours free tonight", min_value=0.5, max_value=12.0, value=3.0, step=0.5
)

st.subheader("What's on your plate?")

with st.form("add_item", clear_on_submit=True):
    title = st.text_input("What is it?", placeholder="e.g. Corporate Strategy pre-read")
    c1, c2 = st.columns(2)
    kind = c1.selectbox("Type", ["case", "quiz", "deliverable"])
    pages = c2.number_input("Pages (0 if not a reading)", 0, 200, 0)
    c3, c4, c5 = st.columns(3)
    familiarity = c3.selectbox("Familiarity", ["new", "some", "strong"])
    due = c4.selectbox("Due", ["class_start", "tonight", "tomorrow_6am", "this_week"])
    weight = c5.selectbox("Weight", ["low", "med", "high"])

    if st.form_submit_button("Add item", type="primary"):
        if not title.strip():
            st.warning("Give it a name first.")
        else:
            st.session_state["items"].append({
                "title": title.strip(),
                "type": kind,
                "pages": int(pages) if pages > 0 else None,
                "familiarity": familiarity,
                "due": due,
                "weight": weight,
            })

if st.session_state["items"]:
    st.subheader(f"{len(st.session_state['items'])} item(s)")
    for i, it in enumerate(st.session_state["items"]):
        c1, c2 = st.columns([9, 1])
        pages_bit = f" · {it['pages']}p" if it["pages"] else ""
        c1.markdown(
            f"**{it['title']}**  \n"
            f"{it['type']}{pages_bit} · {it['familiarity']} · "
            f"due {it['due'].replace('_', ' ')} · {it['weight']} weight"
        )
        if c2.button("✕", key=f"rm{i}", help="Remove"):
            st.session_state["items"].pop(i)
            st.rerun()

    st.divider()
    if st.button("Plan my night", type="primary"):
        with st.spinner("Working out tonight's plan..."):
            try:
                st.session_state["plan"] = get_plan(
                    st.session_state["items"], hours_free
                )
            except Exception as e:
                st.error(f"Couldn't build a plan. {type(e).__name__}: {e}")

    with st.expander("Debug: payload sent to the AI"):
        st.json({"hours_free": hours_free, "items": st.session_state["items"]})
else:
    st.info("Add your first item above.")

if st.session_state["plan"]:
    st.divider()
    render_plan(st.session_state["plan"], hours_free * 60)
