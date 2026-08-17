import streamlit as st

st.set_page_config(page_title="PrepPilot", page_icon="🚀")
st.title("PrepPilot")
st.caption("Tell me tonight's workload. I'll tell you what to do, skim, and skip.")

VERDICT = {
    "do_fully": ("🟢", "DO FULLY"),
    "satisfice": ("🟡", "SATISFICE"),
    "skip": ("🔴", "SKIP"),
}

FAKE_PLAN = {
    "blocks": [
        {"title": "Corporate Strategy pre-read", "start": "19:30", "minutes": 75,
         "verdict": "do_fully",
         "why": "Quiz at class start and the material is new to you",
         "how": ["Read the exhibits before the narrative",
                 "Map the case onto 5 Forces",
                 "Write two questions to ask in class"]},
        {"title": "Valuation problem set", "start": "20:45", "minutes": 45,
         "verdict": "satisfice",
         "why": "Due this week, so a partial pass is enough tonight",
         "how": ["Do questions 1-3 only",
                 "Stop at 45 minutes regardless of progress",
                 "Flag what you skipped for tomorrow"]},
        {"title": "Group PPT review", "start": "21:30", "minutes": 30,
         "verdict": "satisfice",
         "why": "Submission is at 6 AM but you are reviewing, not building",
         "how": ["Check the numbers on slides 4-6",
                 "Send comments in the group chat, do not edit"]},
    ],
    "skipped": [
        {"title": "Optional HBR article",
         "why": "No graded component and nothing left in the budget tonight"},
    ],
    "total_minutes": 150,
    "note": "Valuation gets a 45-minute satisficing pass only.",
}

if "items" not in st.session_state:
    st.session_state["items"] = []
if "plan" not in st.session_state:
    st.session_state["plan"] = None

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
        st.session_state["plan"] = FAKE_PLAN

    with st.expander("Debug: payload that will go to the AI"):
        st.json({"hours_free": hours_free, "items": st.session_state["items"]})
else:
    st.info("Add your first item above.")

if st.session_state["plan"]:
    st.divider()
    render_plan(st.session_state["plan"], hours_free * 60)
