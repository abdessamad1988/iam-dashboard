"""
Moteur d'analyse automatique RH ↔ AD.
Sections A → F — clé de jointure : matricule = employeeID
Activité basée sur lastLogon ; timestamp = date de création/modification du compte AD.
"""
from datetime import datetime, timedelta
import pandas as pd


def run_analyse_ad(
    rh: pd.DataFrame,
    rh_prev: pd.DataFrame,
    ad: pd.DataFrame,
) -> dict:
    now        = datetime.now()
    cutoff_180 = now - timedelta(days=180)
    cutoff_90  = now - timedelta(days=90)

    rh_mats    = set(rh['matricule'].dropna())
    rh_m1_mats = set(rh_prev['matricule'].dropna()) if rh_prev is not None and len(rh_prev) else set()
    ad_ids     = set(ad['employeeID'].dropna())

    # ═══════════════════════════════════════════════════════════════
    # A. Comptes orphelins AD — présents dans AD, absents de RH
    # ═══════════════════════════════════════════════════════════════
    orphan_ids = ad_ids - rh_mats
    a_orphans  = ad[ad['employeeID'].isin(orphan_ids)].copy()

    # ═══════════════════════════════════════════════════════════════
    # B. Comptes à désactiver
    # ═══════════════════════════════════════════════════════════════
    # B1 : actifs dans AD, lastLogon antérieur à 180 jours
    b1 = ad[
        ad['enabled'].astype(bool) &
        ad['lastLogon'].notna() &
        (ad['lastLogon'] < cutoff_180)
    ].copy()
    b1['motif'] = f'Inactif AD > 180j (lastLogon < {cutoff_180.strftime("%Y-%m-%d")})'

    # B2 : employé sorti (absent RH M, présent RH M-1) encore actif dans AD
    departed = rh_m1_mats - rh_mats
    b2 = ad[ad['employeeID'].isin(departed) & ad['enabled'].astype(bool)].copy()
    b2 = b2.merge(
        rh_prev[['matricule', 'nom', 'prenom', 'entite_affectation']].rename(
            columns={'matricule': 'emp_rh', 'entite_affectation': 'entite_rh'}
        ),
        left_on='employeeID', right_on='emp_rh', how='left'
    ).drop(columns='emp_rh', errors='ignore')
    b2['motif'] = 'Employé sorti (absent RH M, présent RH M-1)'

    b_to_deact = (
        pd.concat([b1, b2])
        .drop_duplicates(subset=['employeeID'])
        .reset_index(drop=True)
    )

    # ═══════════════════════════════════════════════════════════════
    # C. Comptes manquants — présents dans RH actifs, absents de AD
    # ═══════════════════════════════════════════════════════════════
    rh_active    = rh[rh['action'] != 'desactiver']
    missing_mats = set(rh_active['matricule']) - ad_ids
    c_missing    = rh_active[rh_active['matricule'].isin(missing_mats)].copy()

    # ═══════════════════════════════════════════════════════════════
    # D. Comptes à risque
    # ═══════════════════════════════════════════════════════════════
    # D1 : comptes bloqués
    d_locked = ad[ad['lockedOut'].astype(bool)].copy()

    # D2 : mots de passe expirés + compte actif
    d_pwd_expired = ad[
        ad['passwordExpired'].astype(bool) & ad['enabled'].astype(bool)
    ].copy()

    # D3 : inactifs > 90 jours (seuil plus court pour l'AD)
    d_inactive_90 = ad[
        ad['enabled'].astype(bool) &
        ad['lastLogon'].notna() &
        (ad['lastLogon'] < cutoff_90)
    ].copy()

    # D4 : lastLogon ≈ timestamp → jamais utilisé depuis création
    # Compte créé (timestamp) mais lastLogon absent ou = timestamp (delta < 1 jour)
    ad_ts = ad.copy()
    ad_ts['_delta'] = (ad_ts['lastLogon'] - ad_ts['timestamp']).abs()
    d_never_used = ad_ts[
        ad_ts['enabled'].astype(bool) &
        (
            ad_ts['lastLogon'].isna() |
            (ad_ts['_delta'] <= timedelta(days=1))
        )
    ].drop(columns='_delta').copy()

    # ═══════════════════════════════════════════════════════════════
    # E. Doublons mail AD
    # ═══════════════════════════════════════════════════════════════
    ad_mail   = ad[ad['mail'].fillna('').str.len() > 0]
    e_dup_mail = (
        ad_mail[ad_mail.duplicated(subset=['mail'], keep=False)]
        .sort_values('mail')
        .copy()
    )

    # ═══════════════════════════════════════════════════════════════
    # F. Incohérences RH ↔ AD
    # ═══════════════════════════════════════════════════════════════
    m = rh.merge(ad, left_on='matricule', right_on='employeeID', how='inner')

    # F1 : displayName AD vs prénom + nom RH
    m['dn_expected'] = m['prenom'].str.strip() + ' ' + m['nom'].str.strip()
    f1_name = m[
        m['displayName'].str.lower().str.strip() != m['dn_expected'].str.lower()
    ][['matricule', 'nom', 'prenom', 'dn_expected', 'displayName']].copy()
    f1_name.columns = ['Matricule', 'Nom RH', 'Prénom RH', 'DisplayName attendu', 'DisplayName AD']

    # F2 : statut enabled AD vs action RH
    rh_active_mats = set(rh[rh['action'] != 'desactiver']['matricule'])
    f2_status = m[
        (m['matricule'].isin(rh_active_mats) & ~m['enabled'].astype(bool)) |
        (~m['matricule'].isin(rh_active_mats) & m['enabled'].astype(bool))
    ][['matricule', 'nom', 'prenom', 'action', 'enabled']].copy()
    f2_status.columns = ['Matricule', 'Nom', 'Prénom', 'Action RH', 'Actif AD']
    f2_status['Actif AD'] = f2_status['Actif AD'].map({True: '✅ Oui', False: '❌ Non'})

    # F3 : department AD vs entite_affectation RH
    f3_dept = m[
        (m['entite_affectation'].fillna('') != '') &
        (m['department'].fillna('') != '') &
        (m['department'].fillna('') != m['entite_affectation'])
    ][['matricule', 'nom', 'prenom', 'entite_affectation', 'department']].copy()
    f3_dept.columns = ['Matricule', 'Nom', 'Prénom', 'Entité RH', 'Département AD']

    # F4 : title AD vs fonction RH
    f4_title = m[
        (m['fonction'].fillna('') != '') &
        (m['title'].fillna('') != '') &
        (m['title'].fillna('') != m['fonction'])
    ][['matricule', 'nom', 'prenom', 'fonction', 'title']].copy()
    f4_title.columns = ['Matricule', 'Nom', 'Prénom', 'Fonction RH', 'Titre AD']

    return {
        # ── Compteurs ─────────────────────────────────────────
        'n_orphans':        len(a_orphans),
        'n_to_deactivate':  len(b_to_deact),
        'n_b1':             len(b1),
        'n_b2':             len(b2),
        'n_missing':        len(c_missing),
        'n_locked':         len(d_locked),
        'n_pwd_expired':    len(d_pwd_expired),
        'n_inactive_90':    len(d_inactive_90),
        'n_never_used':     len(d_never_used),
        'n_dup_mail':       len(e_dup_mail),
        'n_inco_name':      len(f1_name),
        'n_inco_status':    len(f2_status),
        'n_inco_dept':      len(f3_dept),
        'n_inco_title':     len(f4_title),
        # ── DataFrames ────────────────────────────────────────
        'a_orphans':        a_orphans,
        'b_to_deact':       b_to_deact,
        'b1':               b1,
        'b2':               b2,
        'c_missing':        c_missing,
        'd_locked':         d_locked,
        'd_pwd_expired':    d_pwd_expired,
        'd_inactive_90':    d_inactive_90,
        'd_never_used':     d_never_used,
        'e_dup_mail':       e_dup_mail,
        'f1_name':          f1_name,
        'f2_status':        f2_status,
        'f3_dept':          f3_dept,
        'f4_title':         f4_title,
    }
