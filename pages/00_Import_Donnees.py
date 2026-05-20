"""
IAM Dashboard — Page 0 : Import des fichiers mensuels
Upload CSV pour chaque source : RH M, RH M-1, AD, LDAP, Logs
"""
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.style import apply_css

ROOT     = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="Import Données | IAM",
    page_icon="📂",
    layout="wide",
)
apply_css()

# ── Schémas attendus ──────────────────────────────────────────────────────────
SCHEMAS = {
    'rh_M.csv': {
        'label':    'RH — Mois M (courant)',
        'icon':     '👥',
        'required': ['matricule', 'nom', 'prenom', 'entite_affectation', 'site', 'action', 'mois'],
        'optional': ['fonction'],
        'desc':     'Fichier RH du mois en cours — employés actifs + actions (ajouter / modifier / desactiver).',
    },
    'rh_M1.csv': {
        'label':    'RH — Mois M-1 (précédent)',
        'icon':     '🗂️',
        'required': ['matricule', 'nom', 'prenom', 'entite_affectation', 'site', 'mois'],
        'optional': ['fonction'],
        'desc':     'Snapshot RH du mois précédent — utilisé pour détecter les sorties et les mobilités.',
    },
    'ad.csv': {
        'label':    'Active Directory',
        'icon':     '🖥️',
        'required': ['employeeID', 'displayName', 'enabled', 'lastLogon', 'lockedOut', 'passwordExpired'],
        'optional': ['mail', 'department', 'title', 'timestamp'],
        'desc':     'Export AD — comptes, statuts, dernière connexion, verrouillage, expiration MDP.',
    },
    'ldap.csv': {
        'label':    'LDAP',
        'icon':     '🔑',
        'required': ['uid', 'cn', 'enabled'],
        'optional': ['mail', 'role', 'department', 'last_logon', 'description'],
        'desc':     'Export annuaire LDAP — uid, cn, rôle, département, dernière connexion.',
    },
    'logs.csv': {
        'label':    'Logs de provisioning',
        'icon':     '📋',
        'required': ['date', 'matricule', 'action', 'statut'],
        'optional': ['message'],
        'desc':     'Journal des opérations de provisioning (création, modification, erreurs).',
    },
}


def _file_status(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        return {'exists': False}
    try:
        df   = pd.read_csv(path, encoding='utf-8-sig', nrows=0)
        size = path.stat().st_size
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime('%d/%m/%Y %H:%M')
        lines = sum(1 for _ in open(path, encoding='utf-8-sig')) - 1
        return {'exists': True, 'columns': list(df.columns), 'rows': lines, 'size': size, 'mtime': mtime}
    except Exception as e:
        return {'exists': True, 'error': str(e)}


def _validate(df: pd.DataFrame, schema: dict) -> list[str]:
    missing = [c for c in schema['required'] if c not in df.columns]
    return missing


def _save_file(uploaded, filename: str, schema: dict) -> bool:
    try:
        sep = ';' if uploaded.name.endswith('.csv') else ','
        # Try comma first, then semicolon
        try:
            df = pd.read_csv(uploaded, encoding='utf-8-sig')
            if len(df.columns) == 1:
                uploaded.seek(0)
                df = pd.read_csv(uploaded, encoding='utf-8-sig', sep=';')
        except Exception:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, encoding='utf-8-sig', sep=';')

        missing = _validate(df, schema)
        if missing:
            st.error(f"❌ Colonnes obligatoires manquantes : **{', '.join(missing)}**")
            with st.expander("Colonnes détectées dans le fichier"):
                st.code(', '.join(df.columns.tolist()))
            return False

        df.to_csv(DATA_DIR / filename, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture : {e}")
        return False


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔐 IAM Dashboard")
    st.caption("Import des fichiers")
    st.divider()
    if st.button("🔄 Actualiser le statut"):
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📂 Import des Données Mensuelles")
st.caption("Uploadez les fichiers CSV de chaque source pour alimenter le dashboard.")
st.divider()

# ── Statut global ─────────────────────────────────────────────────────────────
statuses = {f: _file_status(f) for f in SCHEMAS}
n_ok     = sum(1 for s in statuses.values() if s.get('exists'))

col_s1, col_s2, col_s3 = st.columns(3)
with col_s1:
    color = '#388E3C' if n_ok == 5 else ('#F57C00' if n_ok > 0 else '#D32F2F')
    st.markdown(
        f'<div style="background:{color};color:white;border-radius:8px;padding:12px 16px;text-align:center;">'
        f'<div style="font-size:1.8rem;font-weight:700;">{n_ok}/5</div>'
        f'<div style="font-size:.85rem;">Fichiers chargés</div></div>',
        unsafe_allow_html=True,
    )
with col_s2:
    if n_ok == 5:
        st.success("✅ Tous les fichiers sont disponibles.")
    elif n_ok == 0:
        st.error("❌ Aucun fichier chargé — données de démo actives.")
    else:
        st.warning(f"⚠️ {5 - n_ok} fichier(s) manquant(s).")
with col_s3:
    if st.button("⚙️ Générer les données de démonstration", use_container_width=True):
        with st.spinner("Génération en cours…"):
            sys.path.insert(0, str(ROOT))
            from generate_data import generate_all
            generate_all(str(DATA_DIR))
        st.cache_data.clear()
        st.success("✅ Données de démonstration générées.")
        st.rerun()

st.divider()

# ── Upload par fichier ────────────────────────────────────────────────────────
for filename, schema in SCHEMAS.items():
    status = statuses[filename]
    icon   = schema['icon']
    label  = schema['label']

    with st.container():
        col_info, col_upload = st.columns([3, 2])

        with col_info:
            # Titre + badge statut
            if status.get('exists') and not status.get('error'):
                badge = '<span style="background:#388E3C;color:white;border-radius:4px;padding:2px 8px;font-size:.78rem;margin-left:8px;">✅ Chargé</span>'
            else:
                badge = '<span style="background:#D32F2F;color:white;border-radius:4px;padding:2px 8px;font-size:.78rem;margin-left:8px;">❌ Manquant</span>'

            st.markdown(f"### {icon} {label} {badge}", unsafe_allow_html=True)
            st.caption(schema['desc'])

            if status.get('exists') and not status.get('error'):
                r, m, sz = status['rows'], status['mtime'], status['size']
                sz_kb = f"{sz/1024:.1f} Ko" if sz < 1024*1024 else f"{sz/1024/1024:.1f} Mo"
                st.markdown(
                    f"<small style='color:#546E7A;'>📄 **{r:,}** lignes &nbsp;|&nbsp; 🕐 {m} &nbsp;|&nbsp; 💾 {sz_kb}</small>",
                    unsafe_allow_html=True,
                )
                # Colonnes requises présentes ?
                present_cols = status.get('columns', [])
                missing_req  = [c for c in schema['required'] if c not in present_cols]
                if missing_req:
                    st.error(f"⚠️ Colonnes manquantes : {', '.join(missing_req)}")

            # Colonnes attendues
            with st.expander("📌 Colonnes attendues", expanded=False):
                req_str = '  '.join([f'`{c}`' for c in schema['required']])
                opt_str = '  '.join([f'`{c}`' for c in schema.get('optional', [])])
                st.markdown(f"**Obligatoires :** {req_str}")
                if opt_str:
                    st.markdown(f"**Optionnelles :** {opt_str}")

        with col_upload:
            uploaded = st.file_uploader(
                f"Importer {filename}",
                type=['csv'],
                key=f"upload_{filename}",
                label_visibility="collapsed",
                help=f"Formats acceptés : CSV (séparateur virgule ou point-virgule, encodage UTF-8 ou UTF-8-BOM)",
            )
            if uploaded is not None:
                with st.spinner("Validation et enregistrement…"):
                    ok = _save_file(uploaded, filename, schema)
                if ok:
                    st.cache_data.clear()
                    st.success(f"✅ **{filename}** importé avec succès !")
                    st.rerun()

            # Bouton suppression
            if status.get('exists'):
                if st.button(f"🗑️ Supprimer {filename}", key=f"del_{filename}"):
                    (DATA_DIR / filename).unlink(missing_ok=True)
                    st.cache_data.clear()
                    st.warning(f"🗑️ **{filename}** supprimé.")
                    st.rerun()

        st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    "💡 **Conseil :** uploadez d'abord `rh_M1.csv` (mois précédent) puis `rh_M.csv` (mois courant) "
    "pour que la détection de mobilité et les analyses LDAP / AD soient correctes.  \n"
    "Encodage recommandé : **UTF-8 avec BOM** (Excel → Enregistrer sous → CSV UTF-8 avec BOM)."
)
