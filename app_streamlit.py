"""Streamlit interface for Parth AI Assistant."""

import asyncio
import os
import streamlit as st
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from ai.agent_manager import AgentManager
from services.services import MessageService, UserCRUD
from dotenv import load_dotenv

load_dotenv()

# Build DATABASE_URL once (just a string, no event loop needed)
_POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
_POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
_POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
_POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin123")
_POSTGRES_DB = os.getenv("POSTGRES_DB", "parth_db")
DATABASE_URL = f"postgresql+asyncpg://{_POSTGRES_USER}:{_POSTGRES_PASSWORD}@{_POSTGRES_HOST}:{_POSTGRES_PORT}/{_POSTGRES_DB}"


def _make_session():
    """Create a fresh engine + session maker each time.

    This ensures the engine is created inside the same event loop
    where it will be used, avoiding the 'attached to a different loop' error.
    """
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=False,
        poolclass=NullPool,  # No pooling - avoids "Event loop is closed" on cleanup
    )
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


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
        model="gpt-5.2",
    )

if "user_crud" not in st.session_state:
    st.session_state.user_crud = UserCRUD(
        model=__import__("models.models", fromlist=["User"]).User
    )

if "db_user_id" not in st.session_state:

    async def init_user():
        SessionLocal = _make_session()
        async with SessionLocal() as db:
            user = await st.session_state.user_crud.get_or_create_by_telegram_id(
                db, telegram_id=1
            )
            return user.id

    st.session_state.db_user_id = asyncio.run(init_user())

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

    # Save user message to database
    async def save_user_message():
        SessionLocal = _make_session()
        async with SessionLocal() as db:
            msg_service = MessageService(db)
            await msg_service.create_message(
                user_id=st.session_state.db_user_id,
                role="user",
                content=prompt,
            )

    asyncio.run(save_user_message())

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

            # Save assistant message to database
            async def save_assistant_message():
                SessionLocal = _make_session()
                async with SessionLocal() as db:
                    msg_service = MessageService(db)
                    await msg_service.create_message(
                        user_id=st.session_state.db_user_id,
                        role="assistant",
                        content=response,
                    )

            asyncio.run(save_assistant_message())
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
    st.text(f"User ID: {st.session_state.db_user_id}")

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
