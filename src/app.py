import streamlit as st
import os
import sys
import time

# Add project root to sys.path to allow 'src' imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from src.core.memory_manager import MemoryManager
from src.services.llm_service import LLMService

# Load environment variables
# Load environment variables
load_dotenv()

# Simple token estimator (approx 4 chars per token)
def estimate_tokens(text: str) -> int:
    return len(text) // 4 if text else 0

def get_dir_size(path):
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except FileNotFoundError:
        pass
    return total

st.set_page_config(page_title="AI Character Memory System", layout="wide")

# --- Session State Initialization ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "rag_latencies" not in st.session_state:
    st.session_state.rag_latencies = []

# Hot-fix: Check for stale MemoryManager instance (due to code updates)
if "memory_manager" in st.session_state:
    import inspect
    try:
        sig = inspect.signature(st.session_state.memory_manager.save_interaction)
        if "user_name" not in sig.parameters:
            st.warning("Detecting code update... Refreshing Memory Manager.")
            del st.session_state["memory_manager"]
            st.rerun()
    except Exception:
        pass

if "memory_manager" not in st.session_state:
    # Ensure directories exist
    os.makedirs("data", exist_ok=True)
    
    profile_path = "data/profile.json"
    vector_db_path = "data/chroma_db"
    
    # Initialize Services
    llm_service = LLMService()
    mm = MemoryManager(profile_path, vector_db_path, llm_service)
    
    st.session_state.memory_manager = mm

# --- Sidebar: Settings & Profile ---
with st.sidebar:
    st.header("⚙️ Settings")
    user_name = st.text_input("Your Name", value="Traveler", key="user_name_input")
    user_persona = st.text_area("Your Persona", value="A mysterious traveler from a distant land.", key="user_persona_input", help="Describe who you are to the character.")
    
    # Check for API Key in environment
    env_api_key = os.getenv("OPENROUTER_API_KEY")
    
    if env_api_key and env_api_key != "sk-or-v1-your-key-here":
        st.session_state.memory_manager.llm_service.set_api_key(env_api_key)
        st.success("✅ API Key loaded from local .env file")
    else:
        st.warning("API Key not found in .env file.")
        api_key_input = st.text_input("Enter OpenRouter API Key (or configure .env)", type="password")
        if api_key_input:
            st.session_state.memory_manager.llm_service.set_api_key(api_key_input)
            st.success("API Key Set!")

    model_name = st.text_input("Model Name", value="x-ai/grok-4.1-fast")
    if model_name != st.session_state.memory_manager.llm_service.model:
        st.session_state.memory_manager.llm_service.set_model(model_name)
        st.success(f"Model set to {model_name}")

    st.divider()
    
    st.header("👤 Character Profile")
    mm = st.session_state.memory_manager
    
    # Simple Profile Editor
    new_name = st.text_input("Name", mm.profile.name)
    if new_name != mm.profile.name:
        mm.profile.name = new_name
        mm.save_profile()
        st.rerun()

    from src.core.presets import DEMO_CHARACTER
    if st.button("Load Demo Character"):
        mm.profile = DEMO_CHARACTER
        mm.save_profile()
        st.rerun()

    with st.expander("Social Context"):
        st.json(mm.profile.context.model_dump())
    
    with st.expander("Personality"):
        st.json(mm.profile.personality.model_dump())
        
    with st.expander("Status"):
        st.write(f"Health: {mm.profile.health.hp}")
        st.write(f"Wealth: {mm.profile.wealth.currency}")

    with st.expander("Daily Log"):
        # Debug Info
        st.caption(f"Total Entries: {len(mm.profile.daily_log)}")
        st.caption(f"Profile Path: {os.path.abspath(mm.json_store.file_path)}")
        
        for log in reversed(mm.profile.daily_log[-5:]):  # Show last 5
            st.caption(f"{log.timestamp.strftime('%Y-%m-%d %H:%M')}")
            st.write(f"**{log.activity}**")
            if log.interacted_with:
                st.write(f"With: {', '.join(log.interacted_with)}")
            st.divider()

# --- Main Area: Chat & Memory ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat with Character")
    
    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Say something..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate Response (Streaming)
        with st.chat_message("assistant"):
            # 1. Retrieve
            start_rag = time.time()
            memories = mm.retrieve_relevant_memories(prompt, n_results=10)
            end_rag = time.time()
            rag_duration = end_rag - start_rag
            
            st.session_state.last_retrieval = memories
            st.session_state.last_rag_time = rag_duration
            
            # Track latency for P95
            st.session_state.rag_latencies.append(rag_duration * 1000)
            
            # 2. Prepare Stream
            context_str = "\n".join([f"- {m['content']}" for m in memories])
            system_prompt = mm._construct_system_prompt(user_name=user_name, user_persona=user_persona)
            
            # [Token Count] 1. Input Tokens Breakdown
            history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in st.session_state.chat_history])
            
            t_system = estimate_tokens(system_prompt)
            t_context = estimate_tokens(context_str)
            t_history = estimate_tokens(history_str)
            t_prompt = estimate_tokens(prompt)
            
            input_tokens = t_system + t_context + t_history + t_prompt

            stream = mm.llm_service.generate_response_stream(system_prompt, prompt, context_str)
            
            # 3. Stream Output
            start_llm = time.time()
            response = st.write_stream(stream)
            end_llm = time.time()
            llm_duration = end_llm - start_llm
            st.session_state.last_llm_time = llm_duration
            
            # [Token Count] 2. Output Tokens
            output_tokens = estimate_tokens(response)
            st.session_state.last_token_usage = {
                "input_total": input_tokens, 
                "output_total": output_tokens,
                "breakdown": {
                    "system": t_system,
                    "context": t_context,
                    "history": t_history,
                    "prompt": t_prompt
                }
            }
            
        # 4. Save to History & Memory
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    # --- Reflection Trigger ---
    st.divider()
    if st.button("🛑 End Conversation & Reflect"):
        with st.spinner("Reflecting on interaction..."):
            # [Token Count] 3. Reflection Tokens
            ref_input_str = str(st.session_state.chat_history)
            ref_input_tokens = estimate_tokens(ref_input_str)

            result = mm.reflect_on_interaction(st.session_state.chat_history, user_name=user_name)
            
            ref_output_tokens = estimate_tokens(result)
            st.caption(f"Reflection Tokens (Est.): Input {ref_input_tokens} | Output {ref_output_tokens}")

            st.success("Reflection Complete!")
            st.info(result)
            # Clear history for next session
            st.session_state.chat_history = []
            st.rerun()

with col2:
    st.subheader("🧠 Memory Inspector")
    st.info("This panel shows what the AI is 'thinking' and retrieving.")
    
    # --- Memory Store Stats ---
    try:
        # 1. Count (Assuming ChromaDB collection is accessible)
        mem_count = mm.vector_store.collection.count()
        
        # 2. Storage
        db_size_mb = get_dir_size("data/chroma_db") / (1024 * 1024)
        
        # 3. P95 Latency
        if st.session_state.rag_latencies:
            sorted_lats = sorted(st.session_state.rag_latencies)
            idx = int(0.95 * len(sorted_lats))
            idx = min(idx, len(sorted_lats) - 1)
            p95_latency = sorted_lats[idx]
        else:
            p95_latency = 0.0
            
        ms_col1, ms_col2, ms_col3 = st.columns(3)
        ms_col1.metric("Entries", f"{mem_count}")
        ms_col2.metric("RAG P95", f"{p95_latency:.0f} ms")
        ms_col3.metric("Storage", f"{db_size_mb:.1f} MB")
        
        st.divider()
    except Exception as e:
        pass

    # Display Timings
    if "last_rag_time" in st.session_state and "last_llm_time" in st.session_state:
        t_col1, t_col2 = st.columns(2)
        t_col1.metric("RAG Time", f"{st.session_state.last_rag_time:.3f}s")
        t_col2.metric("LLM Time", f"{st.session_state.last_llm_time:.3f}s")
        
        if "last_token_usage" in st.session_state:
            usage = st.session_state.last_token_usage
            t_col3, t_col4 = st.columns(2)
            t_col3.metric("Input Tokens (Est)", usage["input_total"])
            t_col4.metric("Output Tokens (Est)", usage["output_total"])
            
            if "breakdown" in usage:
                bd = usage["breakdown"]
                st.caption(f"Breakdown(Tokens): Sys {bd['system']} | Mem {bd['context']} | Hist {bd['history']} | User {bd['prompt']}")

        st.divider()
    
    if "last_retrieval" in st.session_state and st.session_state.last_retrieval:
        st.write("**Memories Retrieved for Last Response:**")
        for res in st.session_state.last_retrieval:
            with st.container(border=True):
                st.caption(f"Distance: {res['distance']:.4f}")
                st.write(res['content'])
    elif st.session_state.chat_history:
        st.write("No memories retrieved yet (or first turn).")

    st.divider()
    with st.expander("🛠️ Memory Management (CRUD)"):
        st.write("Search and edit memories.")
        
        # Search for editing
        col_search, col_btn = st.columns([3, 1])
        with col_search:
            manage_query = st.text_input("Search memories to edit/delete", key="manage_search")
        with col_btn:
            show_recent = st.button("Show Recent")
            
        if manage_query or show_recent:
            if show_recent:
                # Hack: Search for common words or use peek if exposed. 
                # Since we didn't expose peek, we'll search for " " which usually matches everything or just "User I"
                results = mm.vector_store.search("User I replied", n_results=10)
            else:
                results = mm.vector_store.search(manage_query, n_results=5)
            
            for res in results:
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**ID:** `{res['id']}`")
                        st.write(f"**Content:** {res['content']}")
                        st.caption(f"Type: {res['metadata']['type']} | Importance: {res['metadata']['importance']}")
                    
                    with col_b:
                        if st.button("Delete", key=f"del_{res['id']}"):
                            mm.delete_memory(res['id'])
                            st.success("Deleted!")
                            st.rerun()
                            
                    # Edit Form
                    with st.popover("Edit"):
                        new_content = st.text_area("Content", res['content'], key=f"edit_c_{res['id']}")
                        new_type = st.selectbox("Type", ["observation", "thought", "action", "daily_log"], index=["observation", "thought", "action", "daily_log"].index(res['metadata']['type']), key=f"edit_t_{res['id']}")
                        new_imp = st.slider("Importance", 1, 10, res['metadata']['importance'], key=f"edit_i_{res['id']}")
                        
                        if st.button("Save Changes", key=f"save_{res['id']}"):
                            mm.update_memory(res['id'], new_content, new_type, new_imp)
                            st.success("Updated!")
                            st.rerun()

        st.divider()
        st.write("**Add New Memory Manually**")
        with st.form("add_memory_form"):
            add_content = st.text_area("Content")
            add_type = st.selectbox("Type", ["observation", "thought", "action"])
            add_imp = st.slider("Importance", 1, 10, 5)
            if st.form_submit_button("Add Memory"):
                mm.add_memory(add_content, type=add_type, importance=add_imp)
                st.success("Memory Added!")
                st.rerun()
