"""
app.py — AI Council: Multi-Agent Debate System (Streamlit UI)

Run with:
    streamlit run app.py
"""

import io
import html
import uuid
import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from config import PROVIDERS, ROLES, DEFAULT_AGENTS
from agents import Agent, default_council, agent_from_dict
from debate import run_debate, DebateStep
from file_handler import extract_text_from_file, format_context
from rate_limiter import get_registry
from providers import is_provider_configured

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Council",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
if "agents" not in st.session_state:
    st.session_state.agents = default_council()
if "debate_result" not in st.session_state:
    st.session_state.debate_result = None
if "debate_running" not in st.session_state:
    st.session_state.debate_running = False
if "live_steps" not in st.session_state:
    st.session_state.live_steps = []

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
.agent-card {
    border-left: 5px solid;
    padding: 0.8em 1em;
    margin: 0.6em 0;
    border-radius: 4px;
    background: #1e1e2e;
}
.vote-badge {
    display: inline-block;
    padding: 0.2em 0.6em;
    border-radius: 12px;
    font-weight: bold;
    font-size: 0.85em;
    margin-right: 0.4em;
}
.vote-approve  { background:#28a745; color:#fff; }
.vote-reject   { background:#dc3545; color:#fff; }
.vote-revision { background:#ffc107; color:#000; }
.council-approved {
    padding: 1em;
    border-radius: 8px;
    border: 3px solid #28a745;
    background: #0d2b14;
    margin-top: 1em;
}
.council-rejected {
    padding: 1em;
    border-radius: 8px;
    border: 3px solid #dc3545;
    background: #2b0d0d;
    margin-top: 1em;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Agent management & rate limit stats
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⚖️ AI Council")
    st.caption("Multi-agent debate system")

    # --- Current agents ---
    st.subheader("🤖 Council Members")
    agents_to_remove = []
    for i, agent in enumerate(st.session_state.agents):
        col1, col2 = st.columns([4, 1])
        with col1:
            role_cfg = ROLES.get(agent.role, {})
            st.markdown(
                f"<span style='color:{agent.color}'>{agent.icon}</span> "
                f"**{agent.name}**  \n"
                f"<small>{role_cfg.get('label', agent.role)} · "
                f"{PROVIDERS.get(agent.provider, {}).get('name', agent.provider)} · "
                f"{agent.model}</small>",
                unsafe_allow_html=True,
            )
        with col2:
            if st.button("✕", key=f"remove_{agent.id}", help="Remove agent"):
                agents_to_remove.append(agent.id)

    for aid in agents_to_remove:
        st.session_state.agents = [a for a in st.session_state.agents if a.id != aid]
        st.rerun()

    # --- Add new agent ---
    st.divider()
    st.subheader("➕ Add Agent")
    with st.expander("Configure new agent", expanded=False):
        new_name = st.text_input("Agent name", value="New Agent", key="new_agent_name")
        new_role = st.selectbox(
            "Role",
            options=list(ROLES.keys()),
            format_func=lambda r: f"{ROLES[r]['icon']} {ROLES[r]['label']}",
            key="new_agent_role",
        )
        new_provider = st.selectbox(
            "Provider",
            options=list(PROVIDERS.keys()),
            format_func=lambda p: PROVIDERS[p]["name"],
            key="new_agent_provider",
        )
        provider_models = PROVIDERS[new_provider]["models"]
        new_model = st.selectbox("Model", options=provider_models, key="new_agent_model")

        if st.button("Add to Council", type="primary"):
            new_agent = Agent(
                id=str(uuid.uuid4()),
                name=new_name,
                role=new_role,
                provider=new_provider,
                model=new_model,
            )
            st.session_state.agents.append(new_agent)
            st.success(f"Added {new_name}!")
            st.rerun()

    # --- Rate limit stats ---
    st.divider()
    st.subheader("📊 Rate Limit Usage")
    registry = get_registry()
    for stat in registry.all_stats():
        pid = stat["provider"]
        pname = PROVIDERS.get(pid, {}).get("name", pid)
        rpm_pct = stat["rpm_used"] / stat["rpm_limit"] if stat["rpm_limit"] else 0
        rpd_pct = stat["rpd_used"] / stat["rpd_limit"] if stat["rpd_limit"] else 0
        configured = is_provider_configured(pid)
        status = "🟢" if (stat["available"] and configured) else ("🔴" if not configured else "🟡")
        with st.expander(f"{status} {pname}", expanded=False):
            st.progress(min(rpm_pct, 1.0), text=f"RPM: {stat['rpm_used']}/{stat['rpm_limit']}")
            st.progress(min(rpd_pct, 1.0), text=f"RPD: {stat['rpd_used']}/{stat['rpd_limit']}")
            if not configured:
                st.caption("⚠️ API key not configured")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("⚖️ AI Council — Multi-Agent Debate")
st.caption("Ask a question. Watch multiple AI agents debate, critique, and vote on the best answer.")

# --- Question input ---
col_q, col_btn = st.columns([5, 1])
with col_q:
    question = st.text_area(
        "Your question",
        placeholder="e.g. What is the best approach to secure a REST API?",
        height=100,
        key="question_input",
    )

# --- File & URL attachments ---
with st.expander("📎 Attach files or URLs (optional)", expanded=False):
    uploaded_files = st.file_uploader(
        "Upload files",
        accept_multiple_files=True,
        type=["txt", "py", "js", "ts", "md", "json", "csv", "pdf",
              "html", "css", "yaml", "yml", "sh", "go", "rs", "java", "c", "cpp", "h"],
        key="file_uploader",
    )
    url_input = st.text_area(
        "Paste URLs (one per line)",
        placeholder="https://example.com/article",
        height=60,
        key="url_input",
    )

with col_btn:
    st.write("")  # spacer
    st.write("")
    submit = st.button("🚀 Debate!", type="primary", disabled=st.session_state.debate_running)

# ---------------------------------------------------------------------------
# Build context from uploads
# ---------------------------------------------------------------------------
def build_context() -> str:
    file_data = []
    if uploaded_files:
        for f in uploaded_files:
            try:
                text = extract_text_from_file(f.name, f.read())
                file_data.append({"name": f.name, "text": text})
            except Exception as exc:
                st.warning(f"Could not read '{f.name}': {exc}")

    urls = [u.strip() for u in (url_input or "").splitlines() if u.strip()]
    return format_context(file_data, urls)


# ---------------------------------------------------------------------------
# Render a single debate step
# ---------------------------------------------------------------------------
def render_step(step: DebateStep) -> None:
    agent = step.agent
    role_cfg = ROLES.get(agent.role, {})
    step_labels = {
        "proposal": "Initial Proposal",
        "critique": "Critique",
        "revision": "Revision",
        "re-evaluation": "Re-evaluation",
        "specialist": "Analysis",
        "verdict": "Final Verdict",
        "vote": "Vote",
    }
    step_label = step_labels.get(step.step_type, step.step_type.title())
    provider_name = PROVIDERS.get(step.used_provider, {}).get("name", step.used_provider)

    st.markdown(
        f"""<div class="agent-card" style="border-color:{agent.color}">
        <strong style="color:{agent.color}">{agent.icon} {agent.name}</strong>
        &nbsp;·&nbsp;<em>{step_label}</em>
        &nbsp;·&nbsp;<small style="opacity:0.7">{provider_name} / {step.used_model}</small>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown(step.content)
    st.divider()


# ---------------------------------------------------------------------------
# Debate trigger
# ---------------------------------------------------------------------------
if submit:
    if not question.strip():
        st.warning("Please enter a question first.")
    elif not st.session_state.agents:
        st.warning("Add at least one agent to the council.")
    else:
        st.session_state.debate_running = True
        st.session_state.debate_result = None
        st.session_state.live_steps = []

        context_text = build_context()

        debate_placeholder = st.empty()
        steps_so_far: list[DebateStep] = []

        def on_step_callback(step: DebateStep) -> None:
            steps_so_far.append(step)
            with debate_placeholder.container():
                st.subheader("🗣️ Debate in Progress…")
                for s in steps_so_far:
                    render_step(s)

        fallback_warnings: list[str] = []

        def on_fallback_callback(original: str, fallback: str) -> None:
            orig_name = PROVIDERS.get(original, {}).get("name", original)
            fall_name = PROVIDERS.get(fallback, {}).get("name", fallback)
            fallback_warnings.append(
                f"⚠️ {orig_name} rate-limited — falling back to {fall_name}"
            )

        try:
            result = run_debate(
                question=question,
                agents=st.session_state.agents,
                context_text=context_text,
                on_step=on_step_callback,
                on_fallback=on_fallback_callback,
            )
            st.session_state.debate_result = result
        except Exception as exc:
            st.error(f"Debate failed: {exc}")
        finally:
            st.session_state.debate_running = False

        if fallback_warnings:
            for w in fallback_warnings:
                st.warning(w)

        st.rerun()

# ---------------------------------------------------------------------------
# Display completed debate
# ---------------------------------------------------------------------------
if st.session_state.debate_result and not st.session_state.debate_running:
    result = st.session_state.debate_result

    st.subheader("🗣️ Full Debate")
    for step in result["steps"]:
        render_step(step)

    # --- Voting results ---
    st.subheader("🗳️ Council Vote")
    vote_cols = st.columns(len(result["votes"]))
    for col, vote in zip(vote_cols, result["votes"]):
        agent_vote = vote["vote"]
        if agent_vote == "APPROVE":
            badge_cls = "vote-approve"
            emoji = "✅"
        elif agent_vote == "REJECT":
            badge_cls = "vote-reject"
            emoji = "❌"
        else:
            badge_cls = "vote-revision"
            emoji = "🔄"

        role_cfg = ROLES.get(vote["role"], {})
        with col:
            st.markdown(
                f"**{role_cfg.get('icon','🤖')} {vote['agent_name']}**  \n"
                f"<span class='vote-badge {badge_cls}'>{emoji} {agent_vote}</span>",
                unsafe_allow_html=True,
            )
            if vote["reason"]:
                st.caption(vote["reason"])

    st.markdown(f"**Tally:** {result['vote_summary']}")

    # --- Final council decision ---
    safe_answer = html.escape(result["final_answer"]).replace("\n", "<br>")
    if result["approved"]:
        st.markdown(
            f"""<div class="council-approved">
            <h3>✅ Council Approved Solution</h3>
            {safe_answer}
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div class="council-rejected">
            <h3>❌ Council Did Not Reach Consensus</h3>
            {safe_answer}
            </div>""",
            unsafe_allow_html=True,
        )

    if st.button("🔄 New Debate"):
        st.session_state.debate_result = None
        st.rerun()
