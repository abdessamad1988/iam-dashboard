"""
IAM Dashboard — Page 6 : Analyse automatique LDAP ↔ RH
Sous-menu : Synthèse · A Orphelins · B Désactiver · C Manquants · D Risque · E Doublons · F Incohérences
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import load_all_data
from utils.analyse_ldap import run_analyse
from utils.style import apply_css, kpi_card
from utils.pdf_export import pdf_synthese_ldap

st.set_page_config(
    page_title="Analyse LDAP ↔ RH | IAM",
    page_icon="🔍",
    layout="wide",
)
apply_css()

# ── CSS sous-menu ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
div[data-testid="stSidebarContent"] .submenu-title {
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .08em;
    color: #90A4AE;
    text-transform: uppercase;
    margin: 12px 0 4px 4px;
}
div[data-testid="stRadio"] label {
    border-radius: 6px;
    padding: 4px 8px;
    transition: background .15s;
}
div[data-testid="stRadio"] label:hover {
    background: rgba(25,118,210,.08);
}
</style>
""", unsafe_allow_html=True)

# ── Données (partagées entre toutes les sections) ─────────────────────────────
rh, rh_prev, ad, ldap, logs, merged = load_all_data()
r = run_analyse(rh, rh_prev, ldap)

m_label  = rh['mois'].iloc[0]      if not rh.empty      else 'M'
m1_label = rh_prev['mois'].iloc[0] if not rh_prev.empty else 'M-1'
n_inco   = r['n_inco_name'] + r['n_inco_status'] + r['n_inco_dept']

# ── Sidebar avec sous-menu ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔐 IAM Dashboard")
    st.divider()

    st.markdown('<div class="submenu-title">🔍 Analyse LDAP ↔ RH</div>', unsafe_allow_html=True)

    section = st.radio(
        "section",
        options=[
            "📊  Synthèse",
            f"👻  A — Orphelins ({r['n_orphans']})",
            f"🚫  B — À désactiver ({r['n_to_deactivate']})",
            f"❓  C — Manquants ({r['n_missing']})",
            f"⚠️  D — Risque ({r['n_admins']} admins)",
            f"📋  E — Doublons ({r['n_dup_cn'] + r['n_dup_mail']})",
            f"⚡  F — Incohérences ({n_inco})",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("🔄 Rafraîchir"):
        st.cache_data.clear()
        st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _download(df: pd.DataFrame, filename: str, label: str = "⬇️ Exporter CSV") -> None:
    if df.empty:
        return
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(label, csv, filename, "text/csv")


def _enabled_fmt(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    if 'enabled' in d.columns:
        d['enabled'] = d['enabled'].map({True: '✅ Actif', False: '❌ Inactif'})
    return d


COLS_LDAP = [c for c in ['uid', 'cn', 'mail', 'enabled', 'role', 'department', 'last_logon'] if c in ldap.columns]

BADGE = {'critique': '#D32F2F', 'important': '#F57C00', 'info': '#1565C0'}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 SYNTHÈSE
# ═══════════════════════════════════════════════════════════════════════════════
if section.startswith("📊"):
    st.title("🔍 Analyse LDAP ↔ RH — Synthèse")
    st.caption(
        f"RH **{m_label}** · {len(rh)} employés  |  "
        f"RH **{m1_label}** · {len(rh_prev)} employés  |  "
        f"LDAP · {len(ldap)} comptes"
    )
    st.divider()

    col = st.columns(6)
    scores = [
        (r['n_orphans'],                       'A · Orphelins',    BADGE['critique'],  '👻'),
        (r['n_to_deactivate'],                 'B · Désactiver',   BADGE['critique'],  '🚫'),
        (r['n_missing'],                       'C · Manquants',    BADGE['important'], '❓'),
        (r['n_admins'],                        'D · Admins',       BADGE['critique'],  '⚠️'),
        (r['n_dup_cn'] + r['n_dup_mail'],      'E · Doublons',     BADGE['important'], '📋'),
        (n_inco,                               'F · Incohérences', BADGE['info'],      '⚡'),
    ]
    for i, (val, label, color, icon) in enumerate(scores):
        with col[i]:
            st.markdown(kpi_card(val, label, color, icon), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    total_critique  = r['n_orphans'] + r['n_to_deactivate'] + r['n_inactive_admins']
    total_important = r['n_missing'] + r['n_dup_mail'] + r['n_dup_cn']
    if total_critique > 0:
        st.error(f"🔴 **CRITIQUE** : {total_critique}  |  🟠 **IMPORTANT** : {total_important}  |  🔵 **INFO** : {n_inco}")
    elif total_important > 0:
        st.warning(f"🟠 **IMPORTANT** : {total_important}  |  🔵 **INFO** : {n_inco}")
    else:
        st.success("✅ Aucun problème critique détecté.")

    st.divider()
    col_r, col_b = st.columns(2)

    with col_r:
        st.subheader("Radar des anomalies")
        cats = ['Orphelins', 'À désactiver', 'Manquants', 'Admins risque', 'Doublons', 'Incohérences']
        vals = [r['n_orphans'], r['n_to_deactivate'], r['n_missing'],
                r['n_inactive_admins'], r['n_dup_cn'] + r['n_dup_mail'], n_inco]
        fig = go.Figure(go.Scatterpolar(
            r=vals + [vals[0]], theta=cats + [cats[0]],
            fill='toself', fillcolor='rgba(211,47,47,0.15)',
            line=dict(color='#D32F2F', width=2),
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(vals) + 2])),
            showlegend=False, height=320,
            margin=dict(t=20, b=20, l=40, r=40), paper_bgcolor='white',
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("Anomalies par section")
        bar_df = pd.DataFrame({
            'Section': ['A', 'B', 'C', 'D', 'E', 'F'],
            'Nombre':  vals,
            'Gravité': ['Critique', 'Critique', 'Important', 'Critique', 'Important', 'Info'],
        })
        fig2 = px.bar(bar_df, x='Section', y='Nombre', color='Gravité', text='Nombre',
                      color_discrete_map={'Critique': '#D32F2F', 'Important': '#F57C00', 'Info': '#1565C0'})
        fig2.update_traces(textposition='outside')
        fig2.update_layout(height=320, margin=dict(t=20, b=0, l=0, r=0),
                           plot_bgcolor='white', paper_bgcolor='white',
                           legend=dict(orientation='h', y=1.12, x=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.caption("👈 Utilisez le sous-menu pour accéder au détail de chaque section.")

    st.divider()
    col_pdf1, col_pdf2 = st.columns([1, 3])
    with col_pdf1:
        if st.button("📄 Générer Synthèse PDF", use_container_width=True):
            with st.spinner("Génération du PDF…"):
                pdf_bytes = pdf_synthese_ldap(r, rh, ldap, datetime.now())
            st.download_button(
                "⬇️ Télécharger le PDF",
                pdf_bytes,
                f"Synthese_LDAP_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# A. ORPHELINS
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("👻"):
    st.title("👻 A — Comptes Orphelins LDAP")
    st.caption("Présents dans LDAP · absents du fichier RH (anciens employés, comptes non référencés).")
    st.divider()

    df = r['a_orphans']
    n  = r['n_orphans']
    n_active = int(df['enabled'].astype(bool).sum()) if n else 0
    n_admin  = int((df['role'] == 'admin').sum())    if n else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(n,        "Comptes orphelins",  BADGE['critique'],  '👻'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(n_active, "Orphelins actifs",   BADGE['important'], '⚡'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(n_admin,  "Orphelins admins",   '#7B1FA2',          '🛡️'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if n == 0:
        st.success("✅ Aucun compte orphelin détecté.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            status_df = df['enabled'].astype(bool).value_counts().reset_index()
            status_df.columns = ['Statut', 'Nombre']
            status_df['Statut'] = status_df['Statut'].map({True: 'Actif', False: 'Inactif'})
            fig = px.pie(status_df, names='Statut', values='Nombre',
                         color='Statut', color_discrete_map={'Actif': '#D32F2F', 'Inactif': '#90A4AE'},
                         hole=0.45, title="Statut des orphelins")
            fig.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            role_df = df['role'].value_counts().reset_index()
            role_df.columns = ['Rôle', 'Nombre']
            fig2 = px.bar(role_df, x='Rôle', y='Nombre', color='Rôle',
                          color_discrete_map={'admin': '#7B1FA2', 'user': '#1976D2'},
                          title="Répartition par rôle")
            fig2.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader(f"Détail — {n} compte(s) orphelin(s)")
        st.dataframe(_enabled_fmt(df[COLS_LDAP]), use_container_width=True, hide_index=True)
        _download(df, "A_orphelins.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# B. À DÉSACTIVER
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("🚫"):
    st.title("🚫 B — Comptes à Désactiver")
    st.caption("B1 : actifs inactifs depuis > 180 j  |  B2 : employés sortis encore actifs dans LDAP.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(r['n_to_deactivate'], "Total à désactiver",    BADGE['critique'],  '🚫'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_b1'],            "B1 · Inactifs >180 j",  BADGE['important'], '⏰'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_b2'],            "B2 · Employés sortis",  '#7B1FA2',          '🚪'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    tab_all, tab_b1, tab_b2 = st.tabs(["📋 Vue consolidée", "⏰ B1 — Inactifs >180 j", "🚪 B2 — Employés sortis"])

    def _b_table(df, filename):
        if df.empty:
            st.info("Aucun compte dans cette catégorie.")
            return
        cols = [c for c in ['uid', 'cn', 'mail', 'enabled', 'last_logon', 'department', 'role', 'motif'] if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols]), use_container_width=True, hide_index=True)
        _download(df[cols], filename)

    with tab_all:
        df_all = r['b_to_deact']
        if df_all.empty:
            st.success("✅ Aucun compte à désactiver.")
        else:
            motif_df = df_all['motif'].value_counts().reset_index()
            motif_df.columns = ['Motif', 'Nombre']
            fig = px.bar(motif_df, x='Nombre', y='Motif', orientation='h',
                         color='Motif', color_discrete_sequence=['#F57C00', '#7B1FA2'])
            fig.update_layout(height=180, margin=dict(t=10, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            _b_table(df_all, "B_a_desactiver.csv")

    with tab_b1:
        st.markdown("**Critère :** compte actif dans LDAP avec `last_logon` antérieur à 180 jours.")
        _b_table(r['b1'], "B1_inactifs_180j.csv")

    with tab_b2:
        st.markdown("**Critère :** matricule présent en RH M-1, absent en RH M, encore actif dans LDAP.")
        _b_table(r['b2'], "B2_employes_sortis.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# C. MANQUANTS
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("❓"):
    st.title("❓ C — Comptes Manquants dans LDAP")
    st.caption("Employés actifs dans RH (action ≠ desactiver) sans compte correspondant dans LDAP.")
    st.divider()

    df = r['c_missing']
    n  = r['n_missing']
    n_new = int((df['action'] == 'ajouter').sum()) if n else 0
    n_mod = int((df['action'] == 'modifier').sum()) if n else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(n,     "Comptes manquants",      BADGE['critique'],  '❓'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(n_new, "Nouveaux sans compte",    '#388E3C',          '➕'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(n_mod, "Mobilités sans compte",   BADGE['important'], '🔄'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if n == 0:
        st.success("✅ Tous les employés actifs ont un compte LDAP.")
    else:
        if n_new > 0:
            st.error(f"🆘 {n_new} nouvelle(s) embauche(s) sans compte LDAP !")

        col1, col2 = st.columns(2)
        with col1:
            act_df = df['action'].value_counts().reset_index()
            act_df.columns = ['Action', 'Nombre']
            fig = px.pie(act_df, names='Action', values='Nombre',
                         color='Action',
                         color_discrete_map={'ajouter': '#388E3C', 'modifier': '#1976D2', 'RAS': '#90A4AE'},
                         hole=0.45, title="Par action RH")
            fig.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            ent_df = df[df['entite_affectation'] != ''].groupby('entite_affectation').size().reset_index(name='Nombre')
            ent_df.columns = ['Entité', 'Nombre']
            fig2 = px.bar(ent_df.sort_values('Nombre', ascending=True),
                          x='Nombre', y='Entité', orientation='h',
                          color='Nombre', color_continuous_scale='Reds',
                          title="Par entité")
            fig2.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        cols_c = [c for c in ['matricule', 'nom', 'prenom', 'fonction', 'entite_affectation', 'site', 'action'] if c in df.columns]
        st.subheader(f"Détail — {n} compte(s) manquant(s)")
        st.dataframe(df[cols_c], use_container_width=True, hide_index=True)
        _download(df[cols_c], "C_manquants.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# D. RISQUE
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("⚠️"):
    st.title("⚠️ D — Comptes à Risque")
    st.caption("Comptes administrateurs · admins inactifs · comptes sans historique de connexion.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(r['n_admins'],          "Comptes admin",          '#7B1FA2',          '🛡️'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_inactive_admins'], "Admins inactifs >180 j", BADGE['critique'],  '⚠️'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_no_login'],        "Jamais connectés",       BADGE['important'], '🚷'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    tab_adm, tab_ia, tab_nl = st.tabs(["🛡️ Tous les admins", "⚠️ Admins inactifs", "🚷 Jamais connectés"])

    def _d_table(df, filename):
        if df.empty:
            st.info("Aucun compte dans cette catégorie.")
            return
        cols = [c for c in COLS_LDAP if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols]), use_container_width=True, hide_index=True)
        _download(df[cols], filename)

    with tab_adm:
        df_adm = r['d_admins']
        if not df_adm.empty:
            col1, col2 = st.columns(2)
            with col1:
                s_df = df_adm['enabled'].astype(bool).value_counts().reset_index()
                s_df.columns = ['Statut', 'Nombre']
                s_df['Statut'] = s_df['Statut'].map({True: 'Actif', False: 'Inactif'})
                fig = px.pie(s_df, names='Statut', values='Nombre',
                             color='Statut', color_discrete_map={'Actif': '#7B1FA2', 'Inactif': '#90A4AE'},
                             hole=0.45, title="Statut des admins")
                fig.update_layout(height=240, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                d_df = df_adm.groupby('department').size().reset_index(name='Nombre')
                d_df.columns = ['Département', 'Nombre']
                fig2 = px.bar(d_df.sort_values('Nombre', ascending=True),
                              x='Nombre', y='Département', orientation='h',
                              color='Nombre', color_continuous_scale='Purples',
                              title="Admins par département")
                fig2.update_layout(height=240, margin=dict(t=30, b=0, l=0, r=0), coloraxis_showscale=False)
                st.plotly_chart(fig2, use_container_width=True)
        _d_table(df_adm, "D_admins.csv")

    with tab_ia:
        st.markdown("**Critère :** `role=admin` · compte actif · `last_logon` > 180 jours.")
        if r['n_inactive_admins'] > 0:
            st.error(f"🚨 {r['n_inactive_admins']} admin(s) inactif(s) depuis plus de 180 jours !")
        _d_table(r['d_inactive_admins'], "D_admins_inactifs.csv")

    with tab_nl:
        st.markdown("**Critère :** champ `last_logon` vide — aucune connexion enregistrée.")
        _d_table(r['d_no_login'], "D_jamais_connectes.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# E. DOUBLONS
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("📋"):
    st.title("📋 E — Doublons LDAP")
    st.caption("Comptes partageant un même CN (nom complet) ou une même adresse mail.")
    st.divider()

    c1, c2 = st.columns(2)
    with c1: st.markdown(kpi_card(r['n_dup_cn'],   "Doublons CN",   BADGE['critique'],  '📋'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_dup_mail'], "Doublons Mail", BADGE['important'], '📧'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    tab_cn, tab_mail = st.tabs(["📋 Doublons CN", "📧 Doublons Mail"])

    def _e_table(df, filename):
        if df.empty:
            st.success("✅ Aucun doublon détecté.")
            return
        cols = [c for c in COLS_LDAP if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols]), use_container_width=True, hide_index=True)
        _download(df[cols], filename)

    with tab_cn:
        st.markdown(f"**{r['n_dup_cn']} comptes** partagent un CN identique.")
        _e_table(r['e_dup_cn'], "E_doublons_cn.csv")

    with tab_mail:
        if r['n_dup_mail'] > 0:
            st.warning("⚠️ Plusieurs comptes partagent la même adresse mail — risque d'usurpation d'identité.")
        st.markdown(f"**{r['n_dup_mail']} comptes** partagent une adresse mail identique.")
        _e_table(r['e_dup_mail'], "E_doublons_mail.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# F. INCOHÉRENCES
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("⚡"):
    st.title("⚡ F — Incohérences RH ↔ LDAP")
    st.caption("Écarts détectés entre les attributs RH et les attributs LDAP correspondants.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(r['n_inco_name'],   "Noms incohérents",         BADGE['critique'],  '✏️'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_inco_status'], "Statuts incohérents",       BADGE['important'], '🔀'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_inco_dept'],   "Départements incohérents",  BADGE['info'],      '🏢'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if n_inco == 0:
        st.success("✅ Aucune incohérence détectée entre RH et LDAP.")
    else:
        summary_df = pd.DataFrame({
            'Catégorie': ['F1 — Noms', 'F2 — Statuts', 'F3 — Départements'],
            'Nombre':    [r['n_inco_name'], r['n_inco_status'], r['n_inco_dept']],
        })
        fig = px.bar(summary_df, x='Catégorie', y='Nombre', color='Catégorie',
                     color_discrete_map={'F1 — Noms': '#D32F2F', 'F2 — Statuts': '#F57C00', 'F3 — Départements': '#7B1FA2'})
        fig.update_layout(height=220, margin=dict(t=10, b=0, l=0, r=0), showlegend=False,
                          plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    tab_f1, tab_f2, tab_f3 = st.tabs(["✏️ F1 — Noms", "🔀 F2 — Statuts", "🏢 F3 — Départements"])

    def _f_table(df, note, filename):
        st.caption(note)
        if df.empty:
            st.success("✅ Aucune incohérence dans cette catégorie.")
            return
        st.dataframe(df, use_container_width=True, hide_index=True)
        _download(df, filename)

    with tab_f1:
        _f_table(r['f1_name'],   "`CN` LDAP ≠ `Prénom NOM` RH (insensible à la casse).",           "F1_inco_noms.csv")
    with tab_f2:
        _f_table(r['f2_status'], "Compte actif RH ↔ LDAP désactivé, ou inactif RH ↔ LDAP actif.", "F2_inco_statuts.csv")
    with tab_f3:
        _f_table(r['f3_dept'],   "`department` LDAP ≠ `entite_affectation` RH.",                   "F3_inco_dept.csv")
