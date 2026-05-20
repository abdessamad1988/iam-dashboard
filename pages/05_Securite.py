"""
IAM Dashboard — Page 5 : Sécurité & Comptes à Risque
Vue complète : AD + LDAP croisés, score global, alertes priorisées, matrice de risque.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import compute_kpis, load_all_data
from utils.analyse_ad import run_analyse_ad
from utils.analyse_ldap import run_analyse
from utils.style import apply_css, kpi_card

st.set_page_config(page_title="Sécurité | IAM", page_icon="🔐", layout="wide")
apply_css()

with st.sidebar:
    st.markdown("## 🔐 IAM Dashboard")
    st.caption("Sécurité & Comptes à Risque")
    st.divider()
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()

# ── Données ───────────────────────────────────────────────────────────────────
rh, rh_prev, ad, ldap, logs, merged = load_all_data()
kpis   = compute_kpis(rh, rh_prev, ad, ldap, logs, merged)
r_ad   = run_analyse_ad(rh, rh_prev, ad)
r_ldap = run_analyse(rh, rh_prev, ldap)

now      = datetime.now()
cutoff90  = now - timedelta(days=90)
cutoff180 = now - timedelta(days=180)

# ── Calcul du score de sécurité (0 → 100) ────────────────────────────────────
total_accounts = max(len(ad), 1)

penalites = {
    'Comptes bloqués':         (kpis['locked_accounts'],      3.0),
    'MDP expirés':             (kpis['pwd_expired'],           2.0),
    'Inactifs >90j':           (kpis['inactive_90d'],          1.0),
    'Orphelins LDAP actifs':   (int(r_ldap['a_orphans']['enabled'].astype(bool).sum()), 2.5),
    'Admins inactifs LDAP':    (r_ldap['n_inactive_admins'],   3.0),
    'AD jamais utilisés':      (r_ad['n_never_used'],          1.5),
    'Doublons mail LDAP':      (r_ldap['n_dup_mail'],          1.0),
}
total_penalty = sum(n * w for n, w in penalites.values())
raw_score     = max(0, 100 - (total_penalty / total_accounts * 100))
score         = round(raw_score, 1)

score_color = '#388E3C' if score >= 80 else ('#F57C00' if score >= 60 else '#D32F2F')
score_label = 'Bon' if score >= 80 else ('Moyen' if score >= 60 else 'Critique')

# ── Alertes priorisées ────────────────────────────────────────────────────────
alertes = []
if kpis['locked_accounts'] > 0:
    alertes.append(('CRITIQUE', '🔒', f"{kpis['locked_accounts']} compte(s) bloqué(s) dans l'AD — intervention immédiate.", '#D32F2F'))
if r_ldap['n_inactive_admins'] > 0:
    alertes.append(('CRITIQUE', '🛡️', f"{r_ldap['n_inactive_admins']} admin(s) LDAP inactif(s) depuis >180 j.", '#D32F2F'))
n_orphans_actifs = int(r_ldap['a_orphans']['enabled'].astype(bool).sum())
if n_orphans_actifs > 0:
    alertes.append(('CRITIQUE', '👻', f"{n_orphans_actifs} compte(s) orphelin(s) encore actif(s) dans LDAP.", '#D32F2F'))
if kpis['pwd_expired'] > 0:
    alertes.append(('IMPORTANT', '🔑', f"{kpis['pwd_expired']} mot(s) de passe expiré(s) sur comptes actifs.", '#F57C00'))
if r_ad['n_never_used'] > 0:
    alertes.append(('IMPORTANT', '🆕', f"{r_ad['n_never_used']} compte(s) AD jamais utilisé(s) depuis la création (lastLogon ≈ timestamp).", '#F57C00'))
if kpis['inactive_90d'] > 0:
    alertes.append(('IMPORTANT', '💤', f"{kpis['inactive_90d']} compte(s) AD actif(s) sans connexion depuis >90 j.", '#F57C00'))
if r_ldap['n_dup_mail'] > 0:
    alertes.append(('INFO', '📧', f"{r_ldap['n_dup_mail']} doublon(s) d'adresse mail dans LDAP — risque d'usurpation.", '#1565C0'))
if r_ad['n_dup_mail'] > 0:
    alertes.append(('INFO', '📧', f"{r_ad['n_dup_mail']} doublon(s) d'adresse mail dans l'AD.", '#1565C0'))

# ══════════════════════════════════════════════════════════════════════════════
# En-tête
# ══════════════════════════════════════════════════════════════════════════════
st.title("🔐 Sécurité & Comptes à Risque")
st.caption("Supervision consolidée AD + LDAP — alertes priorisées, score de sécurité, matrice de risque.")
st.divider()

# ── Score + KPIs ──────────────────────────────────────────────────────────────
col_score, col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1.5])

with col_score:
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': ' / 100', 'font': {'size': 26}},
        title={'text': f"Score Sécurité<br><span style='font-size:14px;color:{score_color}'>{score_label}</span>",
               'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': score_color, 'thickness': 0.3},
            'steps': [
                {'range': [0,  60], 'color': '#FFEBEE'},
                {'range': [60, 80], 'color': '#FFF8E1'},
                {'range': [80, 100],'color': '#E8F5E9'},
            ],
            'threshold': {'line': {'color': score_color, 'width': 3}, 'value': score},
        },
    ))
    fig_gauge.update_layout(height=200, margin=dict(t=30, b=0, l=20, r=20), paper_bgcolor='white')
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_k1:
    st.markdown(kpi_card(kpis['locked_accounts'], 'Comptes bloqués', '#D32F2F', '🔒'), unsafe_allow_html=True)
with col_k2:
    st.markdown(kpi_card(kpis['pwd_expired'],     'MDP expirés',     '#D32F2F', '🔑'), unsafe_allow_html=True)
with col_k3:
    st.markdown(kpi_card(kpis['inactive_90d'],    'Inactifs >90j',   '#F57C00', '💤'), unsafe_allow_html=True)
with col_k4:
    st.markdown(kpi_card(r_ldap['n_inactive_admins'], 'Admins LDAP inactifs', '#7B1FA2', '🛡️'), unsafe_allow_html=True)
with col_k5:
    st.markdown(kpi_card(n_orphans_actifs, 'Orphelins actifs LDAP', '#D32F2F', '👻'), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Alertes priorisées ────────────────────────────────────────────────────────
st.subheader("🚨 Alertes de sécurité")

n_crit = sum(1 for a in alertes if a[0] == 'CRITIQUE')
n_imp  = sum(1 for a in alertes if a[0] == 'IMPORTANT')
n_info = sum(1 for a in alertes if a[0] == 'INFO')

al1, al2, al3 = st.columns(3)
with al1:
    st.markdown(
        f'<div style="background:#D32F2F;color:white;border-radius:6px;padding:8px 14px;text-align:center;">'
        f'<b style="font-size:1.4rem;">{n_crit}</b><br><small>CRITIQUE</small></div>',
        unsafe_allow_html=True)
with al2:
    st.markdown(
        f'<div style="background:#F57C00;color:white;border-radius:6px;padding:8px 14px;text-align:center;">'
        f'<b style="font-size:1.4rem;">{n_imp}</b><br><small>IMPORTANT</small></div>',
        unsafe_allow_html=True)
with al3:
    st.markdown(
        f'<div style="background:#1565C0;color:white;border-radius:6px;padding:8px 14px;text-align:center;">'
        f'<b style="font-size:1.4rem;">{n_info}</b><br><small>INFO</small></div>',
        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if not alertes:
    st.success("✅ Aucune alerte de sécurité détectée.")
else:
    for niveau, ico, msg, color in alertes:
        st.markdown(
            f'<div style="border-left:4px solid {color};background:{"#FFEBEE" if color=="#D32F2F" else "#FFF8E1" if color=="#F57C00" else "#E3F2FD"};'
            f'padding:8px 14px;margin-bottom:6px;border-radius:0 6px 6px 0;">'
            f'<span style="background:{color};color:white;border-radius:4px;padding:1px 7px;font-size:.75rem;font-weight:700;">{niveau}</span>'
            f' {ico} {msg}</div>',
            unsafe_allow_html=True)

st.divider()

# ── Matrice de risque par entité ──────────────────────────────────────────────
st.subheader("🗺️ Matrice de risque par entité")

risk_df = merged.copy()
risk_df['bloques']     = risk_df['lockedOut'].fillna(False).astype(bool)
risk_df['mdp_expire']  = risk_df['passwordExpired'].fillna(False).astype(bool)
risk_df['inactif_90']  = risk_df['lastLogon'].notna() & (risk_df['lastLogon'] < cutoff90)

by_ent = (
    risk_df[risk_df['entite_affectation'].str.len() > 0]
    .groupby('entite_affectation')
    .agg(
        Total       = ('matricule',    'count'),
        Bloqués     = ('bloques',      'sum'),
        MDP_Expirés = ('mdp_expire',   'sum'),
        Inactifs_90 = ('inactif_90',   'sum'),
    )
    .reset_index()
)
by_ent.rename(columns={'entite_affectation': 'Entité'}, inplace=True)
by_ent['À risque']   = by_ent['Bloqués'] + by_ent['MDP_Expirés'] + by_ent['Inactifs_90']
by_ent['Sains']      = (by_ent['Total'] - by_ent['À risque']).clip(lower=0)
by_ent['% Risque']   = (by_ent['À risque'] / by_ent['Total'] * 100).round(1)
by_ent = by_ent.sort_values('% Risque', ascending=False)

col_mat, col_pie = st.columns([3, 2])

with col_mat:
    fig_mat = go.Figure()
    fig_mat.add_trace(go.Bar(name='Sains',       x=by_ent['Entité'], y=by_ent['Sains'],       marker_color='#388E3C'))
    fig_mat.add_trace(go.Bar(name='Inactifs >90j', x=by_ent['Entité'], y=by_ent['Inactifs_90'], marker_color='#7B1FA2'))
    fig_mat.add_trace(go.Bar(name='MDP expirés', x=by_ent['Entité'], y=by_ent['MDP_Expirés'], marker_color='#F57C00'))
    fig_mat.add_trace(go.Bar(name='Bloqués',     x=by_ent['Entité'], y=by_ent['Bloqués'],     marker_color='#D32F2F'))
    fig_mat.update_layout(
        barmode='stack', plot_bgcolor='white', paper_bgcolor='white',
        height=320, margin=dict(t=10, b=0),
        legend=dict(orientation='h', y=1.12, x=0),
    )
    st.plotly_chart(fig_mat, use_container_width=True)

with col_pie:
    risk_bkd = pd.DataFrame({
        'Risque':   ['Bloqués', 'MDP expirés', 'Inactifs >90j', 'Admins inactifs', 'Orphelins actifs'],
        'Comptes':  [kpis['locked_accounts'], kpis['pwd_expired'], kpis['inactive_90d'],
                     r_ldap['n_inactive_admins'], n_orphans_actifs],
    })
    risk_bkd = risk_bkd[risk_bkd['Comptes'] > 0]
    if not risk_bkd.empty:
        fig_pie = px.pie(
            risk_bkd, names='Risque', values='Comptes',
            color='Risque',
            color_discrete_map={
                'Bloqués':           '#D32F2F',
                'MDP expirés':       '#F57C00',
                'Inactifs >90j':     '#7B1FA2',
                'Admins inactifs':   '#1565C0',
                'Orphelins actifs':  '#880E4F',
            },
            hole=0.45,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            height=320, margin=dict(t=10, b=0), showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# Tableau % risque par entité
with st.expander("📊 Détail % risque par entité"):
    st.dataframe(
        by_ent[['Entité', 'Total', 'Bloqués', 'MDP_Expirés', 'Inactifs_90', 'À risque', '% Risque']]
        .rename(columns={'MDP_Expirés': 'MDP Expirés', 'Inactifs_90': 'Inactifs >90j'}),
        use_container_width=True, hide_index=True
    )

st.divider()

# ── Distribution inactivité ───────────────────────────────────────────────────
st.subheader("📅 Distribution de l'inactivité — lastLogon AD")

ad_copy = ad.copy()
ad_copy['jours_inactif'] = (now - ad_copy['lastLogon']).dt.days.fillna(9999).astype(int)
ad_copy['bucket'] = pd.cut(
    ad_copy['jours_inactif'],
    bins=[0, 7, 30, 90, 180, 365, 100000],
    labels=['< 7 j', '7–30 j', '31–90 j', '91–180 j', '181–365 j', '> 1 an'],
)
dist = ad_copy['bucket'].value_counts().sort_index().reset_index()
dist.columns = ['Inactivité', 'Comptes']

COLORS = ['#388E3C', '#8BC34A', '#FBC02D', '#FF7043', '#D32F2F', '#880E4F']
fig_dist = px.bar(
    dist, x='Inactivité', y='Comptes', color='Inactivité',
    color_discrete_sequence=COLORS, text='Comptes',
)
fig_dist.update_traces(textposition='outside')
fig_dist.update_layout(
    plot_bgcolor='white', paper_bgcolor='white',
    height=280, margin=dict(t=20, b=0), showlegend=False,
)
st.plotly_chart(fig_dist, use_container_width=True)

st.divider()

# ── Onglets détaillés ─────────────────────────────────────────────────────────
st.subheader("🔎 Détail des comptes à risque")

BASE_COLS = ['matricule', 'nom', 'prenom', 'entite_affectation', 'site']
AD_COLS   = ['lastLogon', 'lockedOut', 'passwordExpired', 'enabled']

def _merged_table(condition, extra_cols=None, sort_col=None):
    cols = BASE_COLS + (extra_cols or [])
    df = merged[condition][[c for c in cols if c in merged.columns]].copy()
    if sort_col and sort_col in df.columns:
        df = df.sort_values(sort_col)
    return df

def _csv(df):
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    f"🔒 Bloqués ({kpis['locked_accounts']})",
    f"🔑 MDP expirés ({kpis['pwd_expired']})",
    f"💤 Inactifs >90j ({kpis['inactive_90d']})",
    f"💤 Inactifs >180j ({r_ad['n_b1']})",
    f"🛡️ Admins LDAP à risque ({r_ldap['n_inactive_admins']})",
    f"👻 Orphelins actifs ({n_orphans_actifs})",
])

# ─── Tab 1 : Bloqués ─────────────────────────────────────────────────────────
with tab1:
    st.markdown("**Critère :** `lockedOut = True` dans l'AD — compte verrouillé suite à trop de tentatives.")
    df1 = _merged_table(
        merged['lockedOut'].fillna(False).astype(bool),
        extra_cols=['lastLogon', 'enabled'],
    )
    if df1.empty:
        st.success("✅ Aucun compte bloqué.")
    else:
        df1['enabled'] = df1['enabled'].map({True: '✅', False: '❌'}) if 'enabled' in df1.columns else '—'
        st.error(f"🚨 {len(df1)} compte(s) bloqué(s) — déblocage requis en urgence.")
        st.dataframe(df1, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df1), "bloques_AD.csv", "text/csv")

# ─── Tab 2 : MDP expirés ─────────────────────────────────────────────────────
with tab2:
    st.markdown("**Critère :** `passwordExpired = True` ET `enabled = True` dans l'AD.")
    df2 = _merged_table(
        merged['passwordExpired'].fillna(False).astype(bool) & merged['enabled'].astype(bool),
        extra_cols=['lastLogon', 'enabled'],
    )
    if df2.empty:
        st.success("✅ Aucun mot de passe expiré sur compte actif.")
    else:
        df2['enabled'] = df2['enabled'].map({True: '✅', False: '❌'}) if 'enabled' in df2.columns else '—'
        st.warning(f"⚠️ {len(df2)} compte(s) avec mot de passe expiré.")
        st.dataframe(df2, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df2), "mdp_expires_AD.csv", "text/csv")

# ─── Tab 3 : Inactifs >90j ───────────────────────────────────────────────────
with tab3:
    st.markdown("**Critère :** compte AD actif (`enabled = True`) dont `lastLogon` est antérieur à 90 jours.")
    mask3 = merged['lastLogon'].notna() & (merged['lastLogon'] < cutoff90) & merged['enabled'].astype(bool)
    df3 = _merged_table(mask3, extra_cols=['lastLogon'])
    if not df3.empty:
        df3['Jours inactif'] = (now - df3['lastLogon']).dt.days.astype(int)
        df3 = df3.sort_values('Jours inactif', ascending=False)
    if df3.empty:
        st.success("✅ Aucun compte inactif depuis plus de 90 jours.")
    else:
        st.dataframe(df3, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df3), "inactifs_90j_AD.csv", "text/csv")

# ─── Tab 4 : Inactifs >180j ──────────────────────────────────────────────────
with tab4:
    st.markdown("**Critère :** compte AD actif dont `lastLogon` est antérieur à 180 jours — candidat à la désactivation.")
    df4 = r_ad['b1']
    if df4.empty:
        st.success("✅ Aucun compte inactif depuis plus de 180 jours.")
    else:
        cols4 = [c for c in ['employeeID', 'displayName', 'mail', 'lastLogon', 'timestamp', 'department'] if c in df4.columns]
        st.warning(f"⚠️ {len(df4)} compte(s) à désactiver — inactif(s) depuis >180 j.")
        st.dataframe(df4[cols4], use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df4[cols4]), "inactifs_180j_AD.csv", "text/csv")

# ─── Tab 5 : Admins LDAP à risque ────────────────────────────────────────────
with tab5:
    st.markdown("**Critère :** `role = admin` dans LDAP + compte actif + `last_logon` antérieur à 180 jours.")
    df5 = r_ldap['d_inactive_admins']
    if df5.empty:
        st.success("✅ Aucun admin LDAP inactif depuis plus de 180 jours.")
    else:
        cols5 = [c for c in ['uid', 'cn', 'mail', 'enabled', 'role', 'last_logon', 'department'] if c in df5.columns]
        df5_disp = df5[cols5].copy()
        df5_disp['enabled'] = df5_disp['enabled'].map({True: '✅ Actif', False: '❌ Inactif'})
        st.error(f"🚨 {len(df5)} admin(s) LDAP inactif(s) — accès privilégiés dormants !")
        st.dataframe(df5_disp, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df5_disp), "admins_ldap_inactifs.csv", "text/csv")

    st.divider()
    st.markdown("**Tous les comptes admin LDAP** (`role = admin`) :")
    df5b = r_ldap['d_admins']
    cols5b = [c for c in ['uid', 'cn', 'mail', 'enabled', 'last_logon', 'department'] if c in df5b.columns]
    df5b_disp = df5b[cols5b].copy()
    df5b_disp['enabled'] = df5b_disp['enabled'].map({True: '✅ Actif', False: '❌ Inactif'})
    st.dataframe(df5b_disp, use_container_width=True, hide_index=True)
    st.download_button("⬇️ Exporter tous les admins", _csv(df5b_disp), "admins_ldap_tous.csv", "text/csv")

# ─── Tab 6 : Orphelins actifs ────────────────────────────────────────────────
with tab6:
    st.markdown("**Critère :** compte présent dans LDAP (`uid` sans correspondance `matricule` RH) ET `enabled = True`.")
    df6 = r_ldap['a_orphans'][r_ldap['a_orphans']['enabled'].astype(bool)]
    if df6.empty:
        st.success("✅ Aucun compte orphelin actif dans LDAP.")
    else:
        cols6 = [c for c in ['uid', 'cn', 'mail', 'role', 'department', 'last_logon'] if c in df6.columns]
        df6_disp = df6[cols6].copy()
        st.error(f"🚨 {len(df6)} compte(s) orphelin(s) actif(s) — accès non autorisé potentiel !")
        st.dataframe(df6_disp, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Exporter CSV", _csv(df6_disp), "orphelins_actifs_ldap.csv", "text/csv")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"🔐 Score calculé sur {total_accounts} comptes AD  |  "
    f"Pénalités : bloqués ×3 · MDP ×2 · inactifs ×1 · admins inactifs ×3 · orphelins ×2.5  |  "
    f"Mis à jour : {now.strftime('%d/%m/%Y %H:%M')}"
)
