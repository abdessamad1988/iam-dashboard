"""
IAM Dashboard — Page 7 : Analyse automatique RH ↔ AD
Sous-menu : Synthèse · A Orphelins · B Désactiver · C Manquants · D Risque · E Doublons · F Incohérences
Activité basée sur lastLogon | Création basée sur timestamp
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
from utils.analyse_ad import run_analyse_ad
from utils.style import apply_css, kpi_card
from utils.pdf_export import pdf_synthese_ad

st.set_page_config(
    page_title="Analyse RH ↔ AD | IAM",
    page_icon="🖥️",
    layout="wide",
)
apply_css()

st.markdown("""
<style>
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

# ── Données ───────────────────────────────────────────────────────────────────
rh, rh_prev, ad, ldap, logs, merged = load_all_data()
r = run_analyse_ad(rh, rh_prev, ad)

m_label  = rh['mois'].iloc[0]      if not rh.empty      else 'M'
m1_label = rh_prev['mois'].iloc[0] if not rh_prev.empty else 'M-1'
n_inco   = r['n_inco_name'] + r['n_inco_status'] + r['n_inco_dept'] + r['n_inco_title']

# ── Sidebar sous-menu ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔐 IAM Dashboard")
    st.divider()

    st.markdown(
        '<div style="font-size:.72rem;font-weight:700;letter-spacing:.08em;color:#90A4AE;'
        'text-transform:uppercase;margin:12px 0 4px 4px;">🖥️ Analyse RH ↔ AD</div>',
        unsafe_allow_html=True,
    )

    section = st.radio(
        "section_ad",
        options=[
            "📊  Synthèse",
            f"👻  A — Orphelins AD ({r['n_orphans']})",
            f"🚫  B — À désactiver ({r['n_to_deactivate']})",
            f"❓  C — Manquants ({r['n_missing']})",
            f"⚠️  D — Risque ({r['n_locked'] + r['n_pwd_expired']})",
            f"📧  E — Doublons mail ({r['n_dup_mail']})",
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
    if 'lockedOut' in d.columns:
        d['lockedOut'] = d['lockedOut'].map({True: '🔒 Oui', False: '—'})
    if 'passwordExpired' in d.columns:
        d['passwordExpired'] = d['passwordExpired'].map({True: '⚠️ Oui', False: '—'})
    return d


COLS_AD = [c for c in ['employeeID', 'displayName', 'mail', 'enabled', 'department',
                        'title', 'lastLogon', 'lockedOut', 'passwordExpired', 'timestamp'] if c in ad.columns]

BADGE = {'critique': '#D32F2F', 'important': '#F57C00', 'info': '#1565C0'}


# ═══════════════════════════════════════════════════════════════════════════════
# 📊 SYNTHÈSE
# ═══════════════════════════════════════════════════════════════════════════════
if section.startswith("📊"):
    st.title("🖥️ Analyse RH ↔ AD — Synthèse")
    st.caption(
        f"RH **{m_label}** · {len(rh)} employés  |  "
        f"AD · {len(ad)} comptes  |  "
        f"Jointure : `matricule = employeeID`  |  "
        f"Activité : `lastLogon` vs `timestamp`"
    )
    st.divider()

    col = st.columns(6)
    scores = [
        (r['n_orphans'],                                  'A · Orphelins',    BADGE['critique'],  '👻'),
        (r['n_to_deactivate'],                            'B · Désactiver',   BADGE['critique'],  '🚫'),
        (r['n_missing'],                                  'C · Manquants',    BADGE['important'], '❓'),
        (r['n_locked'] + r['n_pwd_expired'],              'D · Risque',       BADGE['critique'],  '⚠️'),
        (r['n_dup_mail'],                                 'E · Doublons',     BADGE['important'], '📧'),
        (n_inco,                                          'F · Incohérences', BADGE['info'],      '⚡'),
    ]
    for i, (val, label, color, icon) in enumerate(scores):
        with col[i]:
            st.markdown(kpi_card(val, label, color, icon), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    total_critique  = r['n_orphans'] + r['n_to_deactivate'] + r['n_locked']
    total_important = r['n_missing'] + r['n_dup_mail'] + r['n_pwd_expired']
    if total_critique > 0:
        st.error(f"🔴 **CRITIQUE** : {total_critique}  |  🟠 **IMPORTANT** : {total_important}  |  🔵 **INFO** : {n_inco}")
    elif total_important > 0:
        st.warning(f"🟠 **IMPORTANT** : {total_important}  |  🔵 **INFO** : {n_inco}")
    else:
        st.success("✅ Aucun problème critique détecté.")

    st.divider()

    # ── Indicateurs lastLogon ──────────────────────────────────────
    st.subheader("📅 Activité AD — lastLogon vs timestamp")
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.markdown(kpi_card(r['n_inactive_90'],  "Inactifs >90 j",          '#F57C00', '⏰'), unsafe_allow_html=True)
    with col_m2:
        st.markdown(kpi_card(r['n_b1'],           "Inactifs >180 j",         '#D32F2F', '⛔'), unsafe_allow_html=True)
    with col_m3:
        st.markdown(kpi_card(r['n_never_used'],   "Jamais utilisés (≈ création)", '#7B1FA2', '🆕'), unsafe_allow_html=True)
    with col_m4:
        st.markdown(kpi_card(r['n_locked'],       "Comptes bloqués",         '#D32F2F', '🔒'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_r, col_b = st.columns(2)

    with col_r:
        st.subheader("Radar des anomalies")
        cats = ['Orphelins', 'À désactiver', 'Manquants', 'Bloqués', 'Doublons', 'Incohérences']
        vals = [r['n_orphans'], r['n_to_deactivate'], r['n_missing'],
                r['n_locked'], r['n_dup_mail'], n_inco]
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
                pdf_bytes = pdf_synthese_ad(r, rh, ad, datetime.now())
            st.download_button(
                "⬇️ Télécharger le PDF",
                pdf_bytes,
                f"Synthese_AD_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# A. ORPHELINS AD
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("👻"):
    st.title("👻 A — Comptes Orphelins AD")
    st.caption("Présents dans AD (`employeeID`) · absents du fichier RH (`matricule`).")
    st.divider()

    df = r['a_orphans']
    n  = r['n_orphans']
    n_active  = int(df['enabled'].astype(bool).sum())             if n else 0
    n_locked  = int(df['lockedOut'].astype(bool).sum())           if n else 0
    n_expired = int(df['passwordExpired'].astype(bool).sum())     if n else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card(n,        "Orphelins AD",       BADGE['critique'],  '👻'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(n_active, "Orphelins actifs",   BADGE['important'], '⚡'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(n_locked, "Bloqués",            BADGE['critique'],  '🔒'), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card(n_expired,"MDP expirés",        BADGE['important'], '🔑'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if n == 0:
        st.success("✅ Aucun compte orphelin détecté dans l'AD.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            s_df = df['enabled'].astype(bool).value_counts().reset_index()
            s_df.columns = ['Statut', 'Nombre']
            s_df['Statut'] = s_df['Statut'].map({True: 'Actif', False: 'Inactif'})
            fig = px.pie(s_df, names='Statut', values='Nombre',
                         color='Statut', color_discrete_map={'Actif': '#D32F2F', 'Inactif': '#90A4AE'},
                         hole=0.45, title="Statut des orphelins")
            fig.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            dept_df = df.groupby('department').size().reset_index(name='Nombre')
            dept_df.columns = ['Département', 'Nombre']
            fig2 = px.bar(dept_df.sort_values('Nombre', ascending=True),
                          x='Nombre', y='Département', orientation='h',
                          color='Nombre', color_continuous_scale='Reds',
                          title="Par département")
            fig2.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader(f"Détail — {n} compte(s) orphelin(s)")
        cols_show = [c for c in ['employeeID', 'displayName', 'mail', 'enabled',
                                 'department', 'lastLogon', 'timestamp', 'lockedOut', 'passwordExpired'] if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols_show]), use_container_width=True, hide_index=True)
        _download(df[cols_show], "A_orphelins_AD.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# B. À DÉSACTIVER
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("🚫"):
    st.title("🚫 B — Comptes AD à Désactiver")
    st.caption("B1 : actifs inactifs > 180 j (lastLogon)  |  B2 : employés sortis encore actifs dans AD.")
    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(r['n_to_deactivate'], "Total à désactiver",    BADGE['critique'],  '🚫'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_b1'],            "B1 · lastLogon >180 j", BADGE['important'], '⏰'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_b2'],            "B2 · Employés sortis",  '#7B1FA2',          '🚪'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    tab_all, tab_b1, tab_b2 = st.tabs(["📋 Vue consolidée", "⏰ B1 — lastLogon >180 j", "🚪 B2 — Employés sortis"])

    COLS_B = [c for c in ['employeeID', 'displayName', 'mail', 'enabled',
                           'lastLogon', 'timestamp', 'department', 'motif'] if c in ad.columns or c == 'motif']

    def _b_table(df, filename):
        if df.empty:
            st.info("Aucun compte dans cette catégorie.")
            return
        cols = [c for c in COLS_B if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols]), use_container_width=True, hide_index=True)
        _download(df[cols], filename)

    with tab_all:
        df_all = r['b_to_deact']
        if df_all.empty:
            st.success("✅ Aucun compte AD à désactiver.")
        else:
            motif_df = df_all['motif'].value_counts().reset_index()
            motif_df.columns = ['Motif', 'Nombre']
            fig = px.bar(motif_df, x='Nombre', y='Motif', orientation='h',
                         color='Motif', color_discrete_sequence=['#F57C00', '#7B1FA2'])
            fig.update_layout(height=150, margin=dict(t=10, b=0, l=0, r=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            _b_table(df_all, "B_a_desactiver_AD.csv")

    with tab_b1:
        st.markdown("**Critère :** compte AD actif (`enabled=True`) dont le `lastLogon` est antérieur à 180 jours.")
        _b_table(r['b1'], "B1_inactifs_180j_AD.csv")

    with tab_b2:
        st.markdown("**Critère :** employé présent en RH M-1, absent en RH M (sorti), encore actif dans AD.")
        _b_table(r['b2'], "B2_sortis_actifs_AD.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# C. MANQUANTS
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("❓"):
    st.title("❓ C — Comptes Manquants dans AD")
    st.caption("Employés actifs dans RH (action ≠ desactiver) sans compte correspondant dans AD.")
    st.divider()

    df = r['c_missing']
    n  = r['n_missing']
    n_new = int((df['action'] == 'ajouter').sum()) if n else 0
    n_mod = int((df['action'] == 'modifier').sum()) if n else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card(n,     "Comptes manquants",   BADGE['critique'],  '❓'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(n_new, "Nouvelles embauches", '#388E3C',          '➕'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(n_mod, "Mobilités sans compte", BADGE['important'], '🔄'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if n == 0:
        st.success("✅ Tous les employés actifs ont un compte AD.")
    else:
        if n_new > 0:
            st.error(f"🆘 {n_new} nouvelle(s) embauche(s) sans compte AD !")
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
                          color='Nombre', color_continuous_scale='Reds', title="Par entité")
            fig2.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        cols_c = [c for c in ['matricule', 'nom', 'prenom', 'fonction', 'entite_affectation', 'site', 'action'] if c in df.columns]
        st.subheader(f"Détail — {n} compte(s) manquant(s)")
        st.dataframe(df[cols_c], use_container_width=True, hide_index=True)
        _download(df[cols_c], "C_manquants_AD.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# D. RISQUE
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("⚠️"):
    st.title("⚠️ D — Comptes AD à Risque")
    st.caption("Comptes bloqués · mots de passe expirés · inactifs >90 j · jamais utilisés depuis création (lastLogon ≈ timestamp).")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card(r['n_locked'],      "Comptes bloqués",        BADGE['critique'],  '🔒'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_pwd_expired'], "MDP expirés (actifs)",   BADGE['critique'],  '🔑'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_inactive_90'], "Inactifs >90 j",         BADGE['important'], '⏰'), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card(r['n_never_used'],  "Jamais utilisés",        '#7B1FA2',          '🆕'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    tab_lock, tab_pwd, tab_i90, tab_nu = st.tabs([
        "🔒 Bloqués", "🔑 MDP expirés", "⏰ Inactifs >90 j", "🆕 Jamais utilisés"
    ])

    COLS_D = [c for c in ['employeeID', 'displayName', 'mail', 'enabled',
                           'lastLogon', 'timestamp', 'department', 'lockedOut', 'passwordExpired'] if c in ad.columns]

    def _d_table(df, note, filename):
        st.caption(note)
        if df.empty:
            st.success("✅ Aucun compte dans cette catégorie.")
            return
        cols = [c for c in COLS_D if c in df.columns]
        st.dataframe(_enabled_fmt(df[cols]), use_container_width=True, hide_index=True)
        _download(df[cols], filename)

    with tab_lock:
        _d_table(r['d_locked'],
                 "Comptes avec `lockedOut = True` — intervention immédiate requise.",
                 "D1_bloques.csv")

    with tab_pwd:
        _d_table(r['d_pwd_expired'],
                 "Comptes actifs avec `passwordExpired = True` — réinitialisation requise.",
                 "D2_mdp_expires.csv")

    with tab_i90:
        _d_table(r['d_inactive_90'],
                 "Comptes actifs dont `lastLogon` est antérieur à 90 jours.",
                 "D3_inactifs_90j.csv")

    with tab_nu:
        _d_table(r['d_never_used'],
                 "Comptes actifs dont `lastLogon` est absent ou égal à `timestamp` (jamais utilisés depuis la création).",
                 "D4_jamais_utilises.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# E. DOUBLONS
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("📧"):
    st.title("📧 E — Doublons Mail AD")
    st.caption("Comptes AD partageant une même adresse mail — risque d'usurpation d'identité.")
    st.divider()

    st.markdown(kpi_card(r['n_dup_mail'], "Doublons mail AD", BADGE['important'], '📧'), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    df = r['e_dup_mail']
    if df.empty:
        st.success("✅ Aucun doublon d'adresse mail détecté dans l'AD.")
    else:
        st.warning(f"⚠️ {r['n_dup_mail']} comptes partagent une adresse mail identique.")

        # Groupement par mail pour visualiser les groupes de doublons
        mail_grp = df.groupby('mail').size().reset_index(name='Nb comptes')
        mail_grp = mail_grp.sort_values('Nb comptes', ascending=False)
        fig = px.bar(mail_grp.head(20), x='mail', y='Nb comptes',
                     color='Nb comptes', color_continuous_scale='Oranges',
                     title="Top 20 mails dupliqués")
        fig.update_layout(height=280, margin=dict(t=30, b=0, l=0, r=0),
                          coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

        cols_show = [c for c in ['employeeID', 'displayName', 'mail', 'enabled',
                                 'department', 'lastLogon'] if c in df.columns]
        st.subheader(f"Détail — {r['n_dup_mail']} compte(s) en doublon")
        st.dataframe(_enabled_fmt(df[cols_show]), use_container_width=True, hide_index=True)
        _download(df[cols_show], "E_doublons_mail_AD.csv")


# ═══════════════════════════════════════════════════════════════════════════════
# F. INCOHÉRENCES
# ═══════════════════════════════════════════════════════════════════════════════
elif section.startswith("⚡"):
    st.title("⚡ F — Incohérences RH ↔ AD")
    st.caption("Écarts détectés entre les attributs RH et les attributs Active Directory correspondants.")
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(kpi_card(r['n_inco_name'],   "DisplayName (F1)", BADGE['critique'],  '✏️'), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card(r['n_inco_status'], "Statut (F2)",      BADGE['important'], '🔀'), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(r['n_inco_dept'],   "Département (F3)", BADGE['info'],      '🏢'), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card(r['n_inco_title'],  "Titre / Fonction (F4)", BADGE['info'],  '💼'), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if n_inco == 0:
        st.success("✅ Aucune incohérence détectée entre RH et AD.")
    else:
        summary_df = pd.DataFrame({
            'Catégorie': ['F1 — DisplayName', 'F2 — Statut', 'F3 — Département', 'F4 — Titre'],
            'Nombre':    [r['n_inco_name'], r['n_inco_status'], r['n_inco_dept'], r['n_inco_title']],
        })
        fig = px.bar(summary_df, x='Catégorie', y='Nombre', color='Catégorie',
                     color_discrete_map={
                         'F1 — DisplayName':  '#D32F2F',
                         'F2 — Statut':       '#F57C00',
                         'F3 — Département':  '#7B1FA2',
                         'F4 — Titre':        '#1565C0',
                     })
        fig.update_layout(height=220, margin=dict(t=10, b=0, l=0, r=0), showlegend=False,
                          plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    tab_f1, tab_f2, tab_f3, tab_f4 = st.tabs([
        "✏️ F1 — DisplayName", "🔀 F2 — Statut", "🏢 F3 — Département", "💼 F4 — Titre"
    ])

    def _f_table(df, note, filename):
        st.caption(note)
        if df.empty:
            st.success("✅ Aucune incohérence dans cette catégorie.")
            return
        st.dataframe(df, use_container_width=True, hide_index=True)
        _download(df, filename)

    with tab_f1:
        _f_table(r['f1_name'],
                 "`displayName` AD ≠ `Prénom NOM` RH (insensible à la casse).",
                 "F1_inco_displayname.csv")
    with tab_f2:
        _f_table(r['f2_status'],
                 "Compte actif RH ↔ AD désactivé, ou inactif RH ↔ AD actif.",
                 "F2_inco_statut.csv")
    with tab_f3:
        _f_table(r['f3_dept'],
                 "`department` AD ≠ `entite_affectation` RH.",
                 "F3_inco_dept.csv")
    with tab_f4:
        _f_table(r['f4_title'],
                 "`title` AD ≠ `fonction` RH.",
                 "F4_inco_titre.csv")
