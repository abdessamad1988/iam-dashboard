"""
Moteur d'analyse automatique LDAP ↔ RH.
Sections A → F conformément aux spécifications.
"""
from datetime import datetime, timedelta
import pandas as pd


def run_analyse(
    rh: pd.DataFrame,
    rh_prev: pd.DataFrame,
    ldap: pd.DataFrame,
) -> dict:
    """
    Retourne un dict contenant les DataFrames et les compteurs
    pour chaque section d'analyse.
    """
    now        = datetime.now()
    cutoff_180 = now - timedelta(days=180)

    rh_mats    = set(rh['matricule'].dropna())
    rh_m1_mats = set(rh_prev['matricule'].dropna()) if rh_prev is not None and len(rh_prev) else set()
    ldap_uids  = set(ldap['uid'].dropna())

    # ═══════════════════════════════════════════════════════════════
    # A. Comptes orphelins — présents dans LDAP, absents de RH
    # ═══════════════════════════════════════════════════════════════
    orphan_uids = ldap_uids - rh_mats
    a_orphans   = ldap[ldap['uid'].isin(orphan_uids)].copy()

    # ═══════════════════════════════════════════════════════════════
    # B. Comptes à désactiver
    # ═══════════════════════════════════════════════════════════════
    # B1 : actifs dans LDAP et inactifs depuis > 180 jours
    b1 = ldap[
        ldap['enabled'].astype(bool) &
        ldap['last_logon'].notna() &
        (ldap['last_logon'] < cutoff_180)
    ].copy()
    b1['motif'] = f'Inactif LDAP > 180j (last_logon < {cutoff_180.strftime("%Y-%m-%d")})'

    # B2 : employé sorti (absent de RH M, présent en RH M-1) mais encore actif dans LDAP
    departed = rh_m1_mats - rh_mats
    b2 = ldap[ldap['uid'].isin(departed) & ldap['enabled'].astype(bool)].copy()
    b2 = b2.merge(
        rh_prev[['matricule', 'nom', 'prenom', 'entite_affectation']].rename(
            columns={'matricule': 'uid_rh', 'entite_affectation': 'entite_rh'}
        ),
        left_on='uid', right_on='uid_rh', how='left'
    ).drop(columns='uid_rh', errors='ignore')
    b2['motif'] = 'Employé sorti (absent RH M, présent RH M-1)'

    b_to_deact = (
        pd.concat([b1, b2])
        .drop_duplicates(subset=['uid'])
        .reset_index(drop=True)
    )

    # ═══════════════════════════════════════════════════════════════
    # C. Comptes manquants — présents dans RH, absents de LDAP
    # ═══════════════════════════════════════════════════════════════
    rh_active    = rh[rh['action'] != 'desactiver']
    missing_mats = set(rh_active['matricule']) - ldap_uids
    c_missing    = rh_active[rh_active['matricule'].isin(missing_mats)].copy()

    # ═══════════════════════════════════════════════════════════════
    # D. Comptes à risque
    # ═══════════════════════════════════════════════════════════════
    d_admins = ldap[ldap['role'] == 'admin'].copy()

    d_inactive_admins = ldap[
        (ldap['role'] == 'admin') &
        ldap['enabled'].astype(bool) &
        ldap['last_logon'].notna() &
        (ldap['last_logon'] < cutoff_180)
    ].copy()

    d_no_login = ldap[ldap['last_logon'].isna()].copy()

    # ═══════════════════════════════════════════════════════════════
    # E. Doublons
    # ═══════════════════════════════════════════════════════════════
    e_dup_cn = (
        ldap[ldap.duplicated(subset=['cn'], keep=False)]
        .sort_values('cn')
        .copy()
    )
    ldap_mail  = ldap[ldap['mail'].fillna('').str.len() > 0]
    e_dup_mail = (
        ldap_mail[ldap_mail.duplicated(subset=['mail'], keep=False)]
        .sort_values('mail')
        .copy()
    )

    # ═══════════════════════════════════════════════════════════════
    # F. Incohérences RH ↔ LDAP
    # ═══════════════════════════════════════════════════════════════
    m = rh.merge(ldap, left_on='matricule', right_on='uid', how='inner')

    # F1 : Nom — cn LDAP vs prénom + nom RH
    m['cn_expected'] = m['prenom'].str.strip() + ' ' + m['nom'].str.strip()
    f1_name = m[
        m['cn'].str.lower().str.strip() != m['cn_expected'].str.lower()
    ][['matricule', 'nom', 'prenom', 'cn_expected', 'cn']].copy()
    f1_name.columns = ['Matricule', 'Nom RH', 'Prénom RH', 'CN attendu', 'CN LDAP']

    # F2 : Statut — enabled LDAP vs action RH
    rh_active_mats = set(rh[rh['action'] != 'desactiver']['matricule'])
    f2_status = m[
        (m['matricule'].isin(rh_active_mats) & ~m['enabled'].astype(bool)) |
        (~m['matricule'].isin(rh_active_mats) & m['enabled'].astype(bool))
    ][['matricule', 'nom', 'prenom', 'action', 'enabled']].copy()
    f2_status.columns = ['Matricule', 'Nom', 'Prénom', 'Action RH', 'Actif LDAP']
    f2_status['Actif LDAP'] = f2_status['Actif LDAP'].map({True: '✅ Oui', False: '❌ Non'})

    # F3 : Département LDAP vs entité RH
    f3_dept = m[
        (m['entite_affectation'].fillna('') != '') &
        (m['department'].fillna('') != '') &
        (m['department'].fillna('') != m['entite_affectation'])
    ][['matricule', 'nom', 'prenom', 'entite_affectation', 'department']].copy()
    f3_dept.columns = ['Matricule', 'Nom', 'Prénom', 'Entité RH', 'Département LDAP']

    return {
        # ── Compteurs ─────────────────────────────────────────
        'n_orphans':         len(a_orphans),
        'n_to_deactivate':   len(b_to_deact),
        'n_b1':              len(b1),
        'n_b2':              len(b2),
        'n_missing':         len(c_missing),
        'n_admins':          len(d_admins),
        'n_inactive_admins': len(d_inactive_admins),
        'n_no_login':        len(d_no_login),
        'n_dup_cn':          len(e_dup_cn),
        'n_dup_mail':        len(e_dup_mail),
        'n_inco_name':       len(f1_name),
        'n_inco_status':     len(f2_status),
        'n_inco_dept':       len(f3_dept),
        # ── DataFrames ────────────────────────────────────────
        'a_orphans':         a_orphans,
        'b_to_deact':        b_to_deact,
        'b1':                b1,
        'b2':                b2,
        'c_missing':         c_missing,
        'd_admins':          d_admins,
        'd_inactive_admins': d_inactive_admins,
        'd_no_login':        d_no_login,
        'e_dup_cn':          e_dup_cn,
        'e_dup_mail':        e_dup_mail,
        'f1_name':           f1_name,
        'f2_status':         f2_status,
        'f3_dept':           f3_dept,
    }
