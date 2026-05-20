"""
IAM Dashboard — Page 2 : Mobilité RH
Comparaison M vs M-1 : entite_affectation, site, fonction.
"""
import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_loader import compute_kpis, load_all_data
from utils.style import apply_css, kpi_card

st.set_page_config(page_title="Mobilité | IAM", page_icon="🔁", layout="wide")
apply_css()

# ── Données ───────────────────────────────────────────────────────────────────
rh, rh_prev, ad, ldap, logs, merged = load_all_data()
kpis = compute_kpis(rh, rh_prev, ad, ldap, logs, merged)

m_label  = rh['mois'].iloc[0]      if not rh.empty      else 'M'
m1_label = rh_prev['mois'].iloc[0] if not rh_prev.empty else 'M-1'

st.title("🔁 Mobilité RH")
st.caption(f"Comparaison **{m1_label}** (M-1) → **{m_label}** (M)  |  Clé : `matricule`")

# ── Règles ────────────────────────────────────────────────────────────────────
with st.expander("ℹ️ Règles de détection"):
    st.markdown(f"""
| Catégorie | Condition |
|---|---|
| **Extra entité + site** | `M_entite ≠ M-1_entite` **et** `M_site ≠ M-1_site` |
| **Extra entité** | `M_entite ≠ M-1_entite` **et** `M_site = M-1_site` |
| **Intra avec chgt site** | `M_entite = M-1_entite` **et** `M_site ≠ M-1_site` |
| **Intra sans chgt site** | `M_entite = M-1_entite` **et** `M_site = M-1_site` |
| **Intra avec chgt fonction** | `M_entite = M-1_entite` **et** `M_fonction ≠ M-1_fonction` |

> Les flags *Intra sans chgt site* et *Intra avec chgt fonction* sont **non exclusifs** :
> un même employé peut cumuler les deux.
""")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Extra entité
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("↗️ Extra entité")

c1, c2, c3 = st.columns(3)
EXTRA_COLOR = {'extra_avec_site': '#D32F2F', 'extra_sans_site': '#F57C00'}
with c1:
    st.markdown(kpi_card(
        kpis['extra_avec_site'] + kpis['extra_sans_site'],
        'Total extra entité', '#D32F2F', '↗️'), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card(
        kpis['extra_avec_site'], 'Extra entité + site', '#D32F2F', '🔀'), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card(
        kpis['extra_sans_site'], 'Extra entité (même site)', '#F57C00', '↔️'), unsafe_allow_html=True)

extra_df = rh[rh['mobilite_type'].isin(['extra_avec_site', 'extra_sans_site'])].copy()

if not extra_df.empty:
    col_l, col_r = st.columns([2, 1])
    with col_l:
        mob_ent = (
            extra_df[extra_df['entite_affectation'] != '']
            .groupby(['entite_affectation', 'mobilite_type'])
            .size().reset_index(name='count')
        )
        fig = px.bar(mob_ent, x='entite_affectation', y='count', color='mobilite_type',
                     color_discrete_map=EXTRA_COLOR, barmode='stack',
                     labels={'entite_affectation': 'Entité M', 'count': 'Mouvements',
                             'mobilite_type': 'Type'})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                          height=280, margin=dict(t=10, b=0),
                          legend=dict(orientation='h', y=1.12))
        st.plotly_chart(fig, use_container_width=True)
    with col_r:
        labels_map = {'extra_avec_site': 'Extra + site', 'extra_sans_site': 'Extra (même site)'}
        cnt = extra_df['mobilite_type'].value_counts().reset_index()
        cnt.columns = ['type', 'count']
        cnt['label'] = cnt['type'].map(labels_map)
        fig2 = px.pie(cnt, names='label', values='count',
                      color='type', color_discrete_map=EXTRA_COLOR, hole=0.45)
        fig2.update_traces(textposition='inside', textinfo='percent+label')
        fig2.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                           height=280, margin=dict(t=10, b=0), showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Intra entité
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("📍 Intra entité  *(même entité d'affectation)*")

# KPI cards — 3 indicateurs + total
ci1, ci2, ci3, ci4 = st.columns(4)
with ci1:
    st.markdown(kpi_card(
        kpis['intra_avec_site'] + kpis['intra_avec_fonction'],
        'Total intra', '#7B1FA2', '📍'), unsafe_allow_html=True)
with ci2:
    st.markdown(kpi_card(
        kpis['flag_intra_site'],
        'Avec chgt site', '#512DA8', '🗺️',
    ), unsafe_allow_html=True)
with ci3:
    st.markdown(kpi_card(
        kpis['flag_intra_sans_site'],
        'Sans chgt site', '#1565C0', '🏢',
    ), unsafe_allow_html=True)
with ci4:
    st.markdown(kpi_card(
        kpis['flag_intra_fonction'],
        'Avec chgt fonction', '#00838F', '💼',
    ), unsafe_allow_html=True)

st.caption(
    f"> **Avec chgt site** = `M_entite = M-1_entite` et `M_site ≠ M-1_site`  "
    f"| **Sans chgt site** = `M_entite = M-1_entite` et `M_site = M-1_site`  "
    f"| **Avec chgt fonction** = `M_entite = M-1_entite` et `M_fonction ≠ M-1_fonction`  *(non exclusifs)*"
)

intra_df = rh[rh['mobilite_type'].isin(['intra_avec_site', 'intra_avec_fonction'])].copy()

INTRA_COLOR = {
    'intra_avec_site':     '#512DA8',
    'intra_avec_fonction': '#00838F',
}
INTRA_LABELS = {
    'intra_avec_site':     'Intra + site',
    'intra_avec_fonction': 'Intra + fonction',
}

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown(f"**Répartition par entité**")
    if not intra_df.empty:
        ient = (
            intra_df[intra_df['entite_affectation'] != '']
            .groupby(['entite_affectation', 'mobilite_type'])
            .size().reset_index(name='count')
        )
        fig3 = px.bar(ient, x='entite_affectation', y='count', color='mobilite_type',
                      color_discrete_map=INTRA_COLOR, barmode='stack',
                      labels={'entite_affectation': 'Entité', 'count': 'Mouvements',
                              'mobilite_type': 'Type'})
        fig3.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                           height=260, margin=dict(t=10, b=0),
                           legend=dict(orientation='h', y=1.12))
        st.plotly_chart(fig3, use_container_width=True)

with col_b:
    st.markdown("**Types intra**")
    if not intra_df.empty:
        icnt = intra_df['mobilite_type'].value_counts().reset_index()
        icnt.columns = ['type', 'count']
        icnt['label'] = icnt['type'].map(INTRA_LABELS)
        fig4 = px.pie(icnt, names='label', values='count',
                      color='type', color_discrete_map=INTRA_COLOR, hole=0.45)
        fig4.update_traces(textposition='inside', textinfo='percent+label')
        fig4.update_layout(plot_bgcolor='white', paper_bgcolor='white',
                           height=260, margin=dict(t=10, b=0), showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Tableau de détail
# ═══════════════════════════════════════════════════════════════════════════════
st.subheader("📄 Détail des mouvements — M-1 → M")

all_mob = rh[rh['mobilite_type'] != 'none'].copy()

# Filtres
fc1, fc2, fc3 = st.columns(3)
TYPE_OPTIONS = {
    'Tous': None,
    'Extra entité + site':      'extra_avec_site',
    'Extra entité (même site)': 'extra_sans_site',
    'Intra avec chgt site':     'intra_avec_site',
    'Intra avec chgt fonction': 'intra_avec_fonction',
}
with fc1:
    f_type = st.selectbox("Type", list(TYPE_OPTIONS.keys()))
with fc2:
    f_ent = st.selectbox("Entité M",  ['Toutes'] + sorted(all_mob['entite_affectation'].dropna().unique().tolist()))
with fc3:
    f_site = st.selectbox("Site M",   ['Tous']   + sorted(all_mob['site'].dropna().unique().tolist()))

filtered = all_mob.copy()
if TYPE_OPTIONS[f_type]:
    filtered = filtered[filtered['mobilite_type'] == TYPE_OPTIONS[f_type]]
if f_ent != 'Toutes':
    filtered = filtered[filtered['entite_affectation'] == f_ent]
if f_site != 'Tous':
    filtered = filtered[filtered['site'] == f_site]

LABEL_TYPE = {
    'extra_avec_site':     '↗ Extra + site',
    'extra_sans_site':     '↔ Extra',
    'intra_avec_site':     '📍 Intra + site',
    'intra_avec_fonction': '💼 Intra + fonction',
}

detail = filtered[[
    'matricule', 'nom', 'prenom',
    'entite_precedente', 'entite_affectation',
    'site_precedent', 'site',
    'fonction_precedente', 'fonction',
    'mobilite_type',
]].copy()
detail.columns = [
    'Matricule', 'Nom', 'Prénom',
    f'Entité {m1_label}', f'Entité {m_label}',
    f'Site {m1_label}',   f'Site {m_label}',
    f'Fonction {m1_label}', f'Fonction {m_label}',
    'Type',
]
detail['Type'] = detail['Type'].map(LABEL_TYPE)

# Indicateurs de changement
detail['Chgt entité'] = detail[f'Entité {m1_label}'] != detail[f'Entité {m_label}']
detail['Chgt site']   = detail[f'Site {m1_label}']   != detail[f'Site {m_label}']
detail['Chgt fonc']   = detail[f'Fonction {m1_label}'] != detail[f'Fonction {m_label}']
detail['Chgt entité'] = detail['Chgt entité'].map({True: '✅', False: ''})
detail['Chgt site']   = detail['Chgt site'].map({True:   '✅', False: ''})
detail['Chgt fonc']   = detail['Chgt fonc'].map({True:   '✅', False: ''})

st.dataframe(detail, use_container_width=True, hide_index=True)
st.caption(f"{len(filtered)} mouvement(s) | M-1 : **{m1_label}**  →  M : **{m_label}**")
