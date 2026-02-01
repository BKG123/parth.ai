"""Streamlit interface for Parth AI Assistant."""

import asyncio
import streamlit as st
from ai.agent_manager import AgentManager

# Page config
st.set_page_config(page_title="Parth AI Assistant", page_icon="🪶", layout="wide")

# Custom CSS for animations
st.markdown(
    """
    <style>
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .thinking {
        animation: pulse 1.5s ease-in-out infinite;
        color: #888;
        font-style: italic;
    }
    .tool-active {
        animation: pulse 1s ease-in-out infinite;
        display: inline-block;
    }
    .spinner {
        display: inline-block;
        animation: rotate 1s linear infinite;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_manager" not in st.session_state:
    # Initialize with user_id=1 for testing
    st.session_state.agent_manager = AgentManager(
        user_id="1",
        name="Parth AI",
        model="gpt-5-mini",
    )

# Header
st.title("🪶 Parth AI Assistant")
st.caption("Your personal AI guide for goals and growth")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response with streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        async def stream_and_display():
            full_response = ""
            started = False
            tool_calls = []
            active_tools = []

            # Show animated thinking initially
            message_placeholder.markdown(
                '<div class="thinking">🪶 Thinking...</div>', unsafe_allow_html=True
            )

            async for event in st.session_state.agent_manager.stream_response(
                prompt,
                history=st.session_state.messages[:-1],  # Exclude current user message
            ):
                if event["type"] == "text":
                    if not started:
                        started = True
                    full_response += event["content"]

                    # Build display with tool calls and response
                    display_text = ""
                    if tool_calls:
                        display_text += (
                            "🔧 **Tools used:** " + ", ".join(tool_calls) + "\n\n"
                        )
                    if active_tools:
                        display_text += (
                            '<div class="tool-active"><span class="spinner">⚙️</span> Running: '
                            + ", ".join(active_tools)
                            + "</div>\n\n"
                        )
                    display_text += full_response + "▌"
                    message_placeholder.markdown(display_text, unsafe_allow_html=True)

                elif event["type"] == "tool_call":
                    tool_name = event["content"]
                    tool_calls.append(f"`{tool_name}`")
                    active_tools.append(f"`{tool_name}`")

                    # Show animated tool call
                    display_text = (
                        '<div class="tool-active"><span class="spinner">⚙️</span> Running: '
                        + ", ".join(active_tools)
                        + "</div>\n\n"
                    )
                    if full_response:
                        display_text += full_response + "▌"
                    message_placeholder.markdown(display_text, unsafe_allow_html=True)

                elif event["type"] == "tool_output":
                    # Tool completed, remove from active list
                    if active_tools:
                        active_tools.pop(0)

            # Final display (no animations)
            display_text = ""
            if tool_calls:
                display_text += "🔧 **Tools used:** " + ", ".join(tool_calls) + "\n\n"
            display_text += full_response
            message_placeholder.markdown(display_text)
            return full_response

        try:
            response = asyncio.run(stream_and_display())
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            message_placeholder.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )

# Sidebar
with st.sidebar:
    st.header("Settings")

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.subheader("Agent Configuration")
    st.text(f"Model: {st.session_state.agent_manager.model_name}")
    st.text(f"Name: {st.session_state.agent_manager.agent_name}")
    st.text(f"User ID: 1")

    st.divider()

    st.markdown("""
    ### About
    Parth AI is your personal guide for setting, tracking, and achieving goals.
    
    Named after Lord Krishna (Partha-sarathi), Parth offers wisdom, compassion, 
    and timely guidance on your journey.
    
    ### Available Features
    - 🎯 Create and track goals
    - 📝 Update goal progress
    - 💬 Send scheduled messages
    - 🔍 View goal history
    - ⚙️ Manage preferences
    """)

    st.divider()

    st.markdown("**Tips:**")
    st.markdown("- Ask about creating a new goal")
    st.markdown("- Check in on your progress")
    st.markdown("- Request insights or guidance")
