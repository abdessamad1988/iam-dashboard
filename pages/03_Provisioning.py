"""
IAM Dashboard — Page 3 : Provisioning AD / LDAP
"""
import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import compute_kpis, load_all_data
from utils.style import apply_css, kpi_card

st.set_page_config(page_title="Provisioning | IAM", page_icon="⚙️", layout="wide")
apply_css()

st.title("⚙️ Provisioning AD / LDAP")
st.caption("Volume d'actions, taux de succès et journal des opérations")
st.divider()

rh, rh_prev, ad, ldap, logs, merged = load_all_data()
kpis = compute_kpis(rh, rh_prev, ad, ldap, logs, merged)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card(kpis['created'],  'Comptes Créés',      '#388E3C', '➕'),  unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card(kpis['modified'], 'Comptes Modifiés',   '#1976D2', '✏️'),  unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card(kpis['disabled'], 'Comptes Désactivés', '#D32F2F', '🚫'),  unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card(f"{kpis['automation_rate']}%", 'Taux Succès', '#F57C00', '✅'), unsafe_allow_html=True)

st.divider()

# ── Row 1 ─────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    st.subheader("Volume par type d'action et entité")
    act_df = (
        rh[rh['action'] != 'RAS']
        [rh['entite_affectation'] != '']
        .groupby(['entite_affectation', 'action'])
        .size()
        .reset_index(name='count')
    )
    fig = px.bar(
        act_df, x='entite_affectation', y='count', color='action',
        color_discrete_map={'ajouter': '#388E3C', 'modifier': '#1976D2', 'desactiver': '#D32F2F'},
        barmode='group',
        labels={'entite_affectation': 'Entité', 'count': 'Opérations', 'action': 'Action'},
    )
    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=320, margin=dict(t=10, b=0),
        legend=dict(orientation='h', y=1.12),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    st.subheader("Taux de succès global")
    rate = kpis['automation_rate']
    color_gauge = '#388E3C' if rate >= 80 else '#F57C00' if rate >= 60 else '#D32F2F'
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rate,
        title={'text': "Succès (%)"},
        number={'suffix': '%', 'font': {'color': color_gauge, 'size': 36}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar':  {'color': color_gauge},
            'steps': [
                {'range': [0,  60], 'color': '#FFEBEE'},
                {'range': [60, 80], 'color': '#FFF8E1'},
                {'range': [80, 100],'color': '#E8F5E9'},
            ],
            'threshold': {'line': {'color': '#B71C1C', 'width': 2}, 'thickness': .75, 'value': 80},
        },
    ))
    fig_g.update_layout(height=320, margin=dict(t=30, b=10, l=20, r=20), paper_bgcolor='white')
    st.plotly_chart(fig_g, use_container_width=True)

st.divider()

# ── Row 2 ─────────────────────────────────────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Succès vs Erreurs")
    log_st = logs.groupby('statut').size().reset_index(name='count')
    fig2 = px.pie(
        log_st, names='statut', values='count',
        color='statut', color_discrete_map={'success': '#388E3C', 'error': '#D32F2F'},
        hole=0.45,
    )
    fig2.update_traces(textposition='inside', textinfo='percent+label')
    fig2.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=280, margin=dict(t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("Activité journalière (30 derniers jours)")
    daily = logs.copy()
    daily['jour'] = daily['date'].dt.date
    daily_cnt = daily.groupby(['jour', 'statut']).size().reset_index(name='count')
    fig3 = px.bar(
        daily_cnt, x='jour', y='count', color='statut',
        color_discrete_map={'success': '#388E3C', 'error': '#D32F2F'},
        barmode='stack',
        labels={'jour': 'Jour', 'count': 'Opérations', 'statut': 'Statut'},
    )
    fig3.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        height=280, margin=dict(t=10, b=0),
        legend=dict(orientation='h', y=1.12),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Logs table ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Journal des opérations")

fc1, fc2, fc3 = st.columns(3)
with fc1:
    f_action = st.selectbox("Action", ['Toutes', 'CREATE_ACCOUNT', 'UPDATE_ACCOUNT', 'DISABLE_ACCOUNT'])
with fc2:
    f_statut = st.selectbox("Statut", ['Tous', 'success', 'error'])
with fc3:
    f_mat = st.text_input("Matricule", placeholder="EMP01001")

filtered = logs.copy()
if f_action != 'Toutes':
    filtered = filtered[filtered['action'] == f_action]
if f_statut != 'Tous':
    filtered = filtered[filtered['statut'] == f_statut]
if f_mat:
    filtered = filtered[filtered['matricule'].str.contains(f_mat.strip(), case=False, na=False)]

disp = filtered.head(200)[['date', 'matricule', 'action', 'statut', 'message']].copy()
disp.columns = ['Date', 'Matricule', 'Action', 'Statut', 'Message']
disp['Statut'] = disp['Statut'].map({'success': '✅ success', 'error': '❌ error'})

st.dataframe(disp, use_container_width=True, hide_index=True)
st.caption(f"{len(filtered)} enregistrement(s) — affichage limité à 200")
