"""
IAM Dashboard — Page 1 : Vue Globale
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from utils.data_loader import compute_kpis, load_all_data
from utils.style import apply_css, kpi_card
from utils.pdf_export import pdf_synthese_globale

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IAM Dashboard",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔐 IAM Dashboard")
    st.caption("Supervision Identity & Access Management")
    st.divider()
    st.markdown(
        "**Navigation**\n"
        "- 🏠 Vue Globale\n"
        "- 🔁 Mobilité\n"
        "- ⚙️ Provisioning\n"
        "- 📋 Qualité\n"
        "- 🔐 Sécurité"
    )
    st.divider()
    if st.button("🔄 Rafraîchir les données"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Mis à jour : {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")
    st.divider()
    if st.button("📄 Télécharger Synthèse PDF", use_container_width=True):
        with st.spinner("Génération du PDF…"):
            pdf_bytes = pdf_synthese_globale(kpis, rh, datetime.now())
        st.download_button(
            "⬇️ Télécharger le PDF",
            pdf_bytes,
            f"Synthese_Globale_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏠 Vue Globale — IAM")
st.caption("Tableau de bord supervision RH · AD · LDAP | V1 MVP")
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
rh, rh_prev, ad, ldap, logs, merged = load_all_data()
kpis = compute_kpis(rh, rh_prev, ad, ldap, logs, merged)

# ── KPI Row 1 ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card(kpis['total_users'],   'Total Utilisateurs',   '#1976D2', '👤'), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card(kpis['active_users'],  'Comptes Actifs',       '#388E3C', '✅'), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card(kpis['new_accounts'],  'Nouveaux Comptes',     '#7B1FA2', '➕'), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card(f"{kpis['automation_rate']}%", 'Taux Automatisation', '#F57C00', '⚙️'), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 2 : Trend + Action pie ────────────────────────────────────────────────
col_trend, col_pie = st.columns([3, 2])

with col_trend:
    st.subheader("Évolution mensuelle des actions RH")
    monthly = (
        rh[rh['action'] != 'RAS']
        .groupby(['mois', 'action'])
        .size()
        .reset_index(name='count')
        .sort_values('mois')
    )
    fig_bar = px.bar(
        monthly, x='mois', y='count', color='action',
        color_discrete_map={'ajouter': '#388E3C', 'modifier': '#1976D2', 'desactiver': '#D32F2F'},
        barmode='group',
        labels={'mois': 'Mois', 'count': 'Actions', 'action': 'Type'},
    )
    fig_bar.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=300, margin=dict(t=10, b=0, l=0, r=0),
        legend=dict(orientation='h', y=1.12, x=0),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_pie:
    st.subheader("Répartition par action")
    action_counts = rh['action'].value_counts().reset_index()
    action_counts.columns = ['action', 'count']
    fig_pie = px.pie(
        action_counts, names='action', values='count',
        color='action',
        color_discrete_map={
            'RAS':       '#BDBDBD',
            'modifier':  '#1976D2',
            'ajouter':   '#388E3C',
            'desactiver':'#D32F2F',
        },
        hole=0.45,
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    fig_pie.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=300, margin=dict(t=10, b=0, l=0, r=0),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 3 : Entity + Site ─────────────────────────────────────────────────────
col_ent, col_site = st.columns(2)

with col_ent:
    st.subheader("Utilisateurs par entité")
    ent = (
        rh[rh['entite_affectation'] != '']
        .groupby('entite_affectation')['matricule']
        .count()
        .reset_index(name='Utilisateurs')
        .rename(columns={'entite_affectation': 'Entité'})
        .sort_values('Utilisateurs', ascending=True)
    )
    fig_ent = px.bar(
        ent, y='Entité', x='Utilisateurs', orientation='h',
        color='Utilisateurs', color_continuous_scale='Blues',
    )
    fig_ent.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=300, margin=dict(t=10, b=0, l=0, r=0),
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_ent, use_container_width=True)

with col_site:
    st.subheader("Répartition par site")
    site_df = rh.groupby('site')['matricule'].count().reset_index(name='Utilisateurs')
    site_df.columns = ['Site', 'Utilisateurs']
    fig_site = px.pie(
        site_df, names='Site', values='Utilisateurs',
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.35,
    )
    fig_site.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=300, margin=dict(t=10, b=0, l=0, r=0),
    )
    st.plotly_chart(fig_site, use_container_width=True)

# ── Alertes rapides ───────────────────────────────────────────────────────────
st.divider()
st.subheader("⚠️ Alertes rapides")
a1, a2, a3, a4 = st.columns(4)
with a1:
    icon = "🔴" if kpis['locked_accounts'] > 0  else "🟢"
    st.metric(f"{icon} Comptes bloqués",         kpis['locked_accounts'])
with a2:
    icon = "🟡" if kpis['pwd_expired']     > 5  else "🟢"
    st.metric(f"{icon} Mots de passe expirés",   kpis['pwd_expired'])
with a3:
    icon = "🟡" if kpis['no_mail']         > 5  else "🟢"
    st.metric(f"{icon} Comptes sans mail",        kpis['no_mail'])
with a4:
    icon = "🔴" if kpis['inconsistencies'] > 10 else "🟢"
    st.metric(f"{icon} Incohérences RH / AD",    kpis['inconsistencies'])

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"IAM Dashboard V1 — {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')} | "
    "Sources : RH · Active Directory · LDAP"
)
