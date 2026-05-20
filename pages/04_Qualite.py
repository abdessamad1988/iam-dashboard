"""
IAM Dashboard — Page 4 : Qualité des données
"""
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import compute_kpis, load_all_data
from utils.style import apply_css, kpi_card

st.set_page_config(page_title="Qualité | IAM", page_icon="📋", layout="wide")
apply_css()

st.title("📋 Qualité des Données")
st.caption("Anomalies, incohérences et score de qualité global")
st.divider()

rh, rh_prev, ad, ldap, logs, merged = load_all_data()
kpis = compute_kpis(rh, rh_prev, ad, ldap, logs, merged)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(kpi_card(kpis['no_mail'],         'Sans Mail LDAP',      '#F57C00', '📧'), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card(kpis['inconsistencies'], 'Incohérences RH / AD','#D32F2F', '⚠️'), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card(kpis['no_entity'],       'Sans Entité',         '#7B1FA2', '🏢'), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card(kpis['log_error'],       'Erreurs Traitement',  '#D32F2F', '❌'), unsafe_allow_html=True)

st.divider()

# ── Score + Radar ─────────────────────────────────────────────────────────────
n_users = max(len(rh), 1)
n_ldap  = max(len(ldap), 1)
n_mer   = max(len(merged), 1)

dim_scores = {
    'Complétude mail':     round((1 - kpis['no_mail']         / n_ldap) * 100, 1),
    'Cohérence RH / AD':   round((1 - kpis['inconsistencies'] / n_mer)  * 100, 1),
    'Entité renseignée':   round((1 - kpis['no_entity']        / n_users)* 100, 1),
    'Succès provisioning': kpis['automation_rate'],
}
global_score = round(sum(dim_scores.values()) / len(dim_scores), 1)

col_gauge, col_radar = st.columns([1, 2])

with col_gauge:
    st.subheader("Score qualité global")
    g_color = '#388E3C' if global_score >= 80 else '#F57C00' if global_score >= 60 else '#D32F2F'
    fig_g = go.Figure(go.Indicator(
        mode="gauge+number",
        value=global_score,
        title={'text': "Qualité globale"},
        number={'suffix': '%', 'font': {'color': g_color, 'size': 36}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar':  {'color': g_color},
            'steps': [
                {'range': [0,  60], 'color': '#FFEBEE'},
                {'range': [60, 80], 'color': '#FFF8E1'},
                {'range': [80, 100],'color': '#E8F5E9'},
            ],
        },
    ))
    fig_g.update_layout(height=300, margin=dict(t=30, b=10, l=20, r=20), paper_bgcolor='white')
    st.plotly_chart(fig_g, use_container_width=True)

with col_radar:
    st.subheader("Qualité par dimension")
    dims   = list(dim_scores.keys())
    values = list(dim_scores.values())

    fig_r = go.Figure()
    fig_r.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=dims + [dims[0]],
        fill='toself',
        fillcolor='rgba(25, 118, 210, 0.18)',
        line=dict(color='#1976D2', width=2),
    ))
    fig_r.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        paper_bgcolor='white',
        height=300,
        margin=dict(t=20, b=20, l=40, r=40),
        showlegend=False,
    )
    st.plotly_chart(fig_r, use_container_width=True)

# ── Anomaly tabs ──────────────────────────────────────────────────────────────
st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["📧 Sans mail", "⚠️ Incohérences RH / AD", "🏢 Sans entité", "❌ Erreurs traitement"])

with tab1:
    df = merged[merged['mail'].fillna('') == ''][
        ['matricule', 'nom', 'prenom', 'entite_affectation', 'site', 'action']
    ].copy()
    df.columns = ['Matricule', 'Nom', 'Prénom', 'Entité', 'Site', 'Action']
    st.write(f"**{len(df)} compte(s) sans adresse mail LDAP**")
    st.dataframe(df, use_container_width=True, hide_index=True)

with tab2:
    m = merged[merged['entite_affectation'].str.len() > 0].copy()
    df2 = m[m['department'].fillna('') != m['entite_affectation']][
        ['matricule', 'nom', 'prenom', 'entite_affectation', 'department', 'fonction', 'title']
    ].copy()
    df2.columns = ['Matricule', 'Nom', 'Prénom', 'Entité RH', 'Dpt AD', 'Fonction RH', 'Titre AD']
    st.write(f"**{len(df2)} incohérence(s) RH ↔ AD**")
    st.dataframe(df2, use_container_width=True, hide_index=True)

with tab3:
    df3 = rh[rh['entite_affectation'].fillna('') == ''][
        ['matricule', 'nom', 'prenom', 'fonction', 'site', 'action']
    ].copy()
    df3.columns = ['Matricule', 'Nom', 'Prénom', 'Fonction', 'Site', 'Action']
    st.write(f"**{len(df3)} utilisateur(s) sans entité d'affectation**")
    st.dataframe(df3, use_container_width=True, hide_index=True)

with tab4:
    df4 = logs[logs['statut'] == 'error'][['date', 'matricule', 'action', 'message']].copy()
    df4.columns = ['Date', 'Matricule', 'Action', 'Message d\'erreur']
    st.write(f"**{len(df4)} erreur(s) de traitement**")
    st.dataframe(df4.head(100), use_container_width=True, hide_index=True)
    if len(df4) > 100:
        st.caption("Affichage limité aux 100 premières erreurs")
