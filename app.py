import streamlit as st

st.set_page_config(page_title="PrepPilot", page_icon="🚀")
st.title("PrepPilot")
st.caption("Tell me tonight's workload. I'll tell you what to do, skim, and skip.")

if "items" not in st.session_state:
    st.session_state["items"] = []

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
    st.button("Plan my night", type="primary", disabled=True)

    with st.expander("Debug: payload sent to the AI"):
        st.json({"hours_free": hours_free, "items": st.session_state["items"]})
else:
    st.info("Add your first item above.")
