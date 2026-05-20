"""Shared CSS + HTML helpers for all dashboard pages."""
import streamlit as st


def apply_css() -> None:
    st.markdown("""
    <style>
    .main .block-container { padding-top: 1.4rem; max-width: 1400px; }
    #MainMenu, footer { visibility: hidden; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    </style>
    """, unsafe_allow_html=True)


def kpi_card(value, label: str, color: str = '#1976D2', icon: str = '') -> str:
    """Return an HTML KPI card."""
    return (
        f'<div style="background:white;border-radius:12px;padding:18px 14px;'
        f'text-align:center;box-shadow:0 2px 10px rgba(0,0,0,.07);'
        f'border-top:4px solid {color};margin-bottom:6px;">'
        f'<div style="font-size:.80rem;color:#757575;margin-bottom:4px;">{icon}&nbsp;{label}</div>'
        f'<div style="font-size:1.85rem;font-weight:700;color:#0D2137;line-height:1.15;">{value}</div>'
        f'</div>'
    )


def section(title: str) -> None:
    st.markdown(f"### {title}")
