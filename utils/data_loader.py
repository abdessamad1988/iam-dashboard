"""Data loading, merging, and KPI computation for the IAM dashboard."""
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / 'data'


def _ensure_data() -> None:
    required = ['rh_M.csv', 'rh_M1.csv', 'ad.csv', 'ldap.csv', 'logs.csv']
    if not all((DATA_DIR / f).exists() for f in required):
        from generate_data import generate_all
        generate_all(str(DATA_DIR))


@st.cache_data(ttl=300, show_spinner="Chargement des données…")
def load_all_data():
    _ensure_data()

    rh      = pd.read_csv(DATA_DIR / 'rh_M.csv',  encoding='utf-8-sig')   # mois M
    rh_prev = pd.read_csv(DATA_DIR / 'rh_M1.csv', encoding='utf-8-sig')   # mois M-1
    ad      = pd.read_csv(DATA_DIR / 'ad.csv',    encoding='utf-8-sig')
    ldap    = pd.read_csv(DATA_DIR / 'ldap.csv',  encoding='utf-8-sig')
    logs    = pd.read_csv(DATA_DIR / 'logs.csv',  encoding='utf-8-sig')

    # ── Type normalisation ────────────────────────────────────
    ad['lastLogon']       = pd.to_datetime(ad['lastLogon'],  errors='coerce')
    ad['timestamp']       = pd.to_datetime(ad['timestamp'],  errors='coerce')
    ad['enabled']         = ad['enabled'].astype(bool)
    ad['lockedOut']       = ad['lockedOut'].astype(bool)
    ad['passwordExpired'] = ad['passwordExpired'].astype(bool)
    # Prestataire = email commence par "v-", sinon Agent
    ad['type_util'] = ad['mail'].apply(
        lambda x: 'Prestataire' if str(x).lower().startswith('v-') else 'Agent'
    )
    ldap['enabled']     = ldap['enabled'].astype(bool)
    ldap['last_logon']  = pd.to_datetime(
        ldap['last_logon'].replace('', pd.NaT), errors='coerce'
    )
    ldap['role']        = ldap['role'].fillna('user')
    ldap['department']  = ldap['department'].fillna('')
    logs['date']        = pd.to_datetime(logs['date'], errors='coerce')

    # ── Fill NaN strings ─────────────────────────────────────
    rh['entite_affectation']      = rh['entite_affectation'].fillna('')
    rh_prev['entite_affectation'] = rh_prev['entite_affectation'].fillna('')
    ldap['mail']                  = ldap['mail'].fillna('')
    ad['mail']                    = ad['mail'].fillna('')

    # ── Calcul mobilite_type par comparaison M vs M-1 ────────
    #
    #  extra_avec_site      : M_entite != M-1_entite  ET  M_site != M-1_site
    #  extra_sans_site      : M_entite != M-1_entite  ET  M_site =  M-1_site
    #  ─── Intra (même entité) ──────────────────────────────────
    #  intra_avec_site      : M_entite = M-1_entite   ET  M_site != M-1_site
    #  intra_avec_fonction  : M_entite = M-1_entite   ET  M_site =  M-1_site  ET M_fonc != M-1_fonc
    #  none                 : aucun changement (ou nouvel arrivant)
    #
    #  Flags transverses (non exclusifs) :
    #  flag_site    : M_entite = M-1_entite  ET  M_site != M-1_site
    #  flag_sans_site: M_entite = M-1_entite ET  M_site =  M-1_site
    #  flag_fonction: M_entite = M-1_entite  ET  M_fonc != M-1_fonc
    # ─────────────────────────────────────────────────────────
    m1 = rh_prev.set_index('matricule')

    def _mobility(row):
        mat = row['matricule']
        if row['action'] == 'ajouter' or mat not in m1.index:
            return 'none', False, False, False
        m_ent   = row['entite_affectation']
        m1_ent  = m1.at[mat, 'entite_affectation']
        m_site  = row['site']
        m1_site = m1.at[mat, 'site']
        m_fonc  = row['fonction']
        m1_fonc = m1.at[mat, 'fonction']
        if not m_ent or not m1_ent:
            return 'none', False, False, False
        ent_chg  = m_ent  != m1_ent
        site_chg = m_site != m1_site
        fonc_chg = m_fonc != m1_fonc
        # Type principal (priorité)
        if ent_chg and site_chg:
            mob = 'extra_avec_site'
        elif ent_chg:
            mob = 'extra_sans_site'
        elif site_chg:
            mob = 'intra_avec_site'
        elif fonc_chg:
            mob = 'intra_avec_fonction'
        else:
            mob = 'none'
        # Flags intra transverses (indépendants du type principal)
        flag_site     = (not ent_chg) and site_chg             # intra avec chgt site
        flag_sans_site = (not ent_chg) and (not site_chg)      # intra sans chgt site (même entité + même site)
        flag_fonction  = (not ent_chg) and fonc_chg            # intra avec chgt fonction
        return mob, flag_site, flag_sans_site, flag_fonction

    result = rh.apply(_mobility, axis=1, result_type='expand')
    rh['mobilite_type']      = result[0]
    rh['flag_intra_site']    = result[1]
    rh['flag_intra_sans_site'] = result[2]
    rh['flag_intra_fonction']  = result[3]

    rh['entite_precedente']  = rh['matricule'].map(m1['entite_affectation'].to_dict())
    rh['site_precedent']     = rh['matricule'].map(m1['site'].to_dict())
    rh['fonction_precedente'] = rh['matricule'].map(m1['fonction'].to_dict())

    # ── Vue fusionnée ─────────────────────────────────────────
    merged = (
        rh
        .merge(ad,   left_on='matricule', right_on='employeeID', how='left')
        .merge(ldap, left_on='matricule', right_on='uid',        how='left',
               suffixes=('', '_ldap'))
    )

    return rh, rh_prev, ad, ldap, logs, merged


def compute_kpis(rh, rh_prev, ad, ldap, logs, merged) -> dict:
    now      = datetime.now()
    cutoff90 = now - timedelta(days=90)

    total_logs   = len(logs)
    success_logs = int((logs['statut'] == 'success').sum()) if total_logs else 0

    # Incohérences RH ↔ AD : departement AD != entite RH
    m = merged[merged['entite_affectation'].str.len() > 0].copy()
    n_inconsistent = int((m['department'].fillna('') != m['entite_affectation']).sum())

    # Désactivations M : employés présents en M-1 absents en M
    n_disabled = int((~rh_prev['matricule'].isin(rh['matricule'])).sum())

    return {
        # ── Utilisateurs ──────────────────────────────────────
        'total_users':      len(rh),
        'prev_users':       len(rh_prev),
        'active_users':     int(ad['enabled'].sum()),
        'inactive_users':   int((~ad['enabled']).sum()),
        'new_accounts':     int((rh['action'] == 'ajouter').sum()),

        # ── Mobilité (M vs M-1) ───────────────────────────────
        'total_mobility':       int((rh['mobilite_type'] != 'none').sum()),
        # Extra
        'extra_avec_site':      int((rh['mobilite_type'] == 'extra_avec_site').sum()),
        'extra_sans_site':      int((rh['mobilite_type'] == 'extra_sans_site').sum()),
        # Intra — type principal
        'intra_avec_site':      int((rh['mobilite_type'] == 'intra_avec_site').sum()),
        'intra_avec_fonction':  int((rh['mobilite_type'] == 'intra_avec_fonction').sum()),
        # Intra — flags transverses (non exclusifs)
        'flag_intra_site':      int(rh['flag_intra_site'].sum()),       # M_entite=M-1_entite ET M_site!=M-1_site
        'flag_intra_sans_site': int(rh['flag_intra_sans_site'].sum()),  # M_entite=M-1_entite ET M_site=M-1_site
        'flag_intra_fonction':  int(rh['flag_intra_fonction'].sum()),   # M_entite=M-1_entite ET M_fonc!=M-1_fonc

        # ── Provisioning ──────────────────────────────────────
        'created':   int((rh['action'] == 'ajouter').sum()),
        'modified':  int((rh['action'] == 'modifier').sum()),
        'disabled':  n_disabled,

        # ── Logs ──────────────────────────────────────────────
        'log_total':       total_logs,
        'log_success':     success_logs,
        'log_error':       total_logs - success_logs,
        'automation_rate': round(success_logs / total_logs * 100, 1) if total_logs else 0,

        # ── Qualité ───────────────────────────────────────────
        'no_mail':         int((ldap['mail'] == '').sum()),
        'no_entity':       int((rh['entite_affectation'] == '').sum()),
        'inconsistencies': n_inconsistent,

        # ── Sécurité ──────────────────────────────────────────
        'locked_accounts': int(ad['lockedOut'].sum()),
        'pwd_expired':     int(ad['passwordExpired'].sum()),
        'inactive_90d':    int((ad['lastLogon'] < cutoff90).sum()),
    }
