from __future__ import annotations

import os
import csv
from datetime import datetime
from pathlib import Path

import streamlit as st

try:
    from chromadb import PersistentClient
except Exception as exc:
    raise ImportError("chromadb is required. Install with `pip install chromadb`.") from exc

DB_PATH = "./hr_chroma_db"
COLLECTION_NAME = "employee_db"
HANDBOOK_FILENAME = "employee-handbook.pdf"
LOG_PATH = Path("access_log.csv")


# -----------------------------
# Data helpers
# -----------------------------
def log_access(email: str, metadata: dict):
    header = [
        "timestamp",
        "email",
        "firstName",
        "lastName",
        "companyName",
        "department",
        "title",
        "country",
        "state",
    ]
    row = [
        datetime.utcnow().isoformat(),
        email,
        metadata.get("firstName", ""),
        metadata.get("lastName", ""),
        metadata.get("companyName", ""),
        metadata.get("department", ""),
        metadata.get("title", ""),
        metadata.get("country", ""),
        metadata.get("state", ""),
    ]

    write_header = not LOG_PATH.exists()
    try:
        with LOG_PATH.open(mode="a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if write_header:
                writer.writerow(header)
            writer.writerow(row)
    except Exception:
        pass


@st.cache_resource
def get_chroma_client(path: str = DB_PATH):
    return PersistentClient(path=path)


def get_collection(client, name: str):
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(name)


# -----------------------------
# UI helpers
# -----------------------------
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #081120;
            --panel: rgba(11, 18, 32, 0.72);
            --panel-2: rgba(15, 23, 42, 0.78);
            --border: rgba(255, 255, 255, 0.10);
            --text: #eff6ff;
            --muted: #9fb0c9;
            --accent: #5eead4;
            --accent-2: #60a5fa;
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #fb7185;
            --shadow: 0 20px 60px rgba(2, 8, 23, 0.42);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(96, 165, 250, 0.20), transparent 28%),
                radial-gradient(circle at top right, rgba(94, 234, 212, 0.16), transparent 24%),
                linear-gradient(180deg, #081120 0%, #0f172a 50%, #111827 100%);
            color: var(--text);
        }

        .block-container {
            max-width: 980px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            display: none;
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            padding: 34px;
            border-radius: 28px;
            border: 1px solid var(--border);
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(8, 17, 32, 0.80));
            box-shadow: var(--shadow);
            margin-bottom: 22px;
        }

        .hero-shell:before {
            content: "";
            position: absolute;
            width: 220px;
            height: 220px;
            right: -40px;
            top: -40px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(96,165,250,0.35), transparent 70%);
            pointer-events: none;
        }

        .hero-shell:after {
            content: "";
            position: absolute;
            width: 180px;
            height: 180px;
            left: -30px;
            bottom: -40px;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(94,234,212,0.25), transparent 70%);
            pointer-events: none;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            color: #cfe4ff;
            font-size: 0.82rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 16px;
            backdrop-filter: blur(8px);
        }

        .hero-title {
            font-size: clamp(2rem, 5vw, 3.3rem);
            line-height: 1.02;
            font-weight: 800;
            margin: 0;
            color: white;
            max-width: 680px;
        }

        .hero-subtitle {
            margin-top: 14px;
            max-width: 720px;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.7;
        }

        .glass-panel {
            background: linear-gradient(180deg, rgba(17, 24, 39, 0.78), rgba(15, 23, 42, 0.82));
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 22px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(14px);
        }

        .section-title {
            margin: 0 0 6px 0;
            font-size: 1.1rem;
            font-weight: 700;
            color: white;
        }

        .section-copy {
            color: var(--muted);
            font-size: 0.95rem;
            margin-bottom: 18px;
        }

        .mini-stat-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 16px;
        }

        .mini-stat {
            border-radius: 18px;
            padding: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
        }

        .mini-stat-label {
            color: var(--muted);
            font-size: 0.82rem;
            margin-bottom: 6px;
        }

        .mini-stat-value {
            color: white;
            font-size: 1rem;
            font-weight: 700;
        }

        .user-card {
            background: linear-gradient(180deg, rgba(10,18,32,0.92), rgba(15,23,42,0.88));
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 24px;
            padding: 24px;
            box-shadow: var(--shadow);
            margin-top: 18px;
        }

        .user-top {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 18px;
        }

        .avatar {
            width: 58px;
            height: 58px;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            font-weight: 800;
            color: white;
            background: linear-gradient(135deg, var(--accent-2), var(--accent));
            box-shadow: 0 12px 24px rgba(96,165,250,0.22);
            flex-shrink: 0;
        }

        .user-name {
            color: white;
            font-size: 1.35rem;
            font-weight: 800;
            margin: 0;
        }

        .user-company {
            color: var(--muted);
            margin-top: 4px;
            font-size: 0.96rem;
        }

        .detail-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 16px;
        }

        .detail-item {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 18px;
            padding: 16px;
        }

        .detail-label {
            color: var(--muted);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 8px;
        }

        .detail-value {
            color: white;
            font-size: 1rem;
            font-weight: 600;
            line-height: 1.45;
            word-break: break-word;
        }

        div[data-testid="stTextInputRootElement"] > div {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            min-height: 56px;
            transition: all 0.2s ease;
        }

        div[data-testid="stTextInputRootElement"] > div:focus-within {
            border-color: rgba(94, 234, 212, 0.55);
            box-shadow: 0 0 0 4px rgba(94, 234, 212, 0.10);
        }

        .stTextInput input {
            color: white !important;
            background: transparent !important;
            font-size: 1rem !important;
        }

        .stTextInput input::placeholder {
            color: #7f93b0 !important;
        }

        .stButton > button,
        .stDownloadButton > button {
            height: 54px;
            border: 0 !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #60a5fa, #22d3ee) !important;
            color: #06101f !important;
            font-weight: 800 !important;
            font-size: 0.98rem !important;
            padding: 0 22px !important;
            box-shadow: 0 14px 34px rgba(34, 211, 238, 0.22) !important;
            transition: transform 0.18s ease, box-shadow 0.18s ease !important;
        }

        .stButton > button:hover,
        .stDownloadButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 18px 40px rgba(34, 211, 238, 0.28) !important;
        }

        [data-testid="stAlert"] {
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(15,23,42,0.76);
            color: white;
        }

        hr {
            border-color: rgba(255,255,255,0.08);
        }

        @media (max-width: 840px) {
            .mini-stat-grid,
            .detail-grid {
                grid-template-columns: 1fr;
            }
            .hero-shell,
            .glass-panel,
            .user-card {
                padding: 18px;
                border-radius: 22px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero():
    st.markdown(
        """
        <div class="hero-shell">
            <div class="eyebrow">Secure internal access</div>
            <h1 class="hero-title">Employee handbook delivery, redesigned.</h1>
            <div class="hero-subtitle">
                A cleaner, more premium experience for verifying employee access and delivering the handbook with confidence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_lookup_panel():
    st.markdown(
        """
        <div class="glass-panel">
            <div class="section-title">Verify work email</div>
            <div class="section-copy">Enter an employee email to check access and unlock the handbook download.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_card(metadata: dict, email: str):
    first = metadata.get("firstName", "").strip()
    last = metadata.get("lastName", "").strip()
    company = metadata.get("companyName", "") or "—"
    department = metadata.get("department", "") or "—"
    title = metadata.get("title", "") or "—"
    country = metadata.get("country", "") or ""
    state = metadata.get("state", "") or ""
    location = ", ".join([x for x in [state, country] if x]) or "—"

    full_name = f"{first} {last}".strip() or "Employee"
    initials = ((first[:1] + last[:1]).upper() or full_name[:2].upper())

    st.markdown(
        f"""
        <div class="user-card">
            <div class="user-top">
                <div class="avatar">{initials}</div>
                <div>
                    <div class="user-name">{full_name}</div>
                    <div class="user-company">{company}</div>
                </div>
            </div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Email</div>
                    <div class="detail-value">{email}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Title</div>
                    <div class="detail-value">{title}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Department</div>
                    <div class="detail-value">{department}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Location</div>
                    <div class="detail-value">{location}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">Verified employee</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Access</div>
                    <div class="detail-value">Handbook download enabled</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer_stats():
    st.markdown(
        """
        <div class="glass-panel" style="margin-top:18px;">
            <div class="section-title">Built for clarity</div>
            <div class="section-copy">The updated layout improves trust, scannability, and perceived quality without changing your access logic.</div>
            <div class="mini-stat-grid">
                <div class="mini-stat">
                    <div class="mini-stat-label">Visual hierarchy</div>
                    <div class="mini-stat-value">Stronger</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-label">First impression</div>
                    <div class="mini-stat-value">Premium</div>
                </div>
                <div class="mini-stat">
                    <div class="mini-stat-label">Interaction feel</div>
                    <div class="mini-stat-value">Modern</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------
# App
# -----------------------------
def main():
    st.set_page_config(
        page_title="HR Document Delivery",
        page_icon="📘",
        layout="centered",
    )

    inject_css()
    render_hero()

    client = get_chroma_client()
    collection = get_collection(client, COLLECTION_NAME)

    render_lookup_panel()
    st.write("")

    left, right = st.columns([4.2, 1.3], vertical_alignment="bottom")
    with left:
        email_input = st.text_input(
            "Work Email",
            value="",
            placeholder="name@company.com",
            label_visibility="collapsed",
        )
    with right:
        check = st.button("Check Access", use_container_width=True)

    if check:
        email = (email_input or "").strip().lower()
        if not email:
            st.warning("Please enter a valid work email.")
            render_footer_stats()
            return

        with st.spinner("Checking access..."):
            try:
                result = collection.get(ids=[email])
            except Exception as exc:
                st.error(f"Lookup error: {exc}")
                render_footer_stats()
                return

        ids = result.get("ids", []) if isinstance(result, dict) else []
        if ids:
            metadatas = result.get("metadatas", [{}])
            metadata = metadatas[0] if metadatas else {}

            st.success("Access granted. Employee verified.")
            render_user_card(metadata, email)
            log_access(email, metadata)

            st.write("")
            if os.path.exists(HANDBOOK_FILENAME):
                try:
                    with open(HANDBOOK_FILENAME, "rb") as fh:
                        pdf_bytes = fh.read()
                    st.download_button(
                        label="Download Employee Handbook",
                        data=pdf_bytes,
                        file_name=HANDBOOK_FILENAME,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as exc:
                    st.warning(f"Could not prepare download: {exc}")
            else:
                st.warning("Employee handbook file is missing from disk.")
        else:
            st.warning("Please delete the email – you don’t work with this company.")

    render_footer_stats()


if __name__ == "__main__":
    main()
