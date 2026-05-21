#!/usr/bin/env python3
"""IAM Dashboard — Sample data generator (RH M / RH M-1, AD, LDAP, Logs)."""
import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

random.seed(42)
np.random.seed(42)

N_BASE = 240   # Effectif M-1

ENTITIES   = ['DSI', 'DRH', 'DAF', 'Direction Générale', 'DCom', 'DProd', 'DLogistique', 'DJuridique']
SITES      = ['Casablanca', 'Rabat', 'Marrakech', 'Agadir', 'Fès', 'Tanger']
FUNCTIONS  = [
    'Ingénieur Système', 'Analyste RH', 'Chef de Projet', 'Développeur Senior',
    'Responsable IT', 'Comptable Principal', 'Directeur Adjoint', 'Chargé Communication',
    'Technicien Réseau', 'Responsable Logistique', 'Juriste', 'Auditeur Interne',
    'Manager Opérationnel', 'Assistant RH', 'Architecte Solution', 'DBA',
    'Contrôleur de Gestion', 'Responsable Sécurité', 'DevOps Engineer', 'Data Analyst',
]
FIRST_NAMES = [
    'Mohamed', 'Ahmed', 'Youssef', 'Khalid', 'Hassan', 'Rachid', 'Omar', 'Ali',
    'Fatima', 'Khadija', 'Laila', 'Nadia', 'Samira', 'Zineb', 'Aicha', 'Meryem',
    'Abdelhamid', 'Mustapha', 'Karim', 'Mehdi', 'Amine', 'Tariq', 'Hamid', 'Samir',
    'Salma', 'Houda', 'Najat', 'Rim', 'Sara', 'Imane', 'Jamal', 'Redouane',
    'Hasnaa', 'Ghita', 'Soumia', 'Ibtissam', 'Abderrahim', 'Mourad', 'Issam', 'Bilal',
]
LAST_NAMES = [
    'Benali', 'El Ouafi', 'Tazi', 'Berrada', 'Alaoui', 'Bennani', 'Chraibi',
    'El Idrissi', 'Bensouda', 'Fassi', 'Kettani', 'Mernissi', 'Belkacem',
    'Bouazza', 'El Amrani', 'Ziani', 'Naciri', 'Cherkaoui', 'Ghali', 'Soussi',
    'Benhaddou', 'El Hajji', 'Filali', 'Benkirane', 'Lazrak', 'Tahiri',
    'El Mansouri', 'Bakkali', 'Sefrioui', 'El Ouazzani',
]
ERROR_MSGS = [
    'Erreur LDAP: connexion refusée',
    'Timeout AD: délai dépassé',
    'Attribut obligatoire manquant',
    'Echec authentification service account',
    'Erreur synchronisation AD-LDAP',
    'Violation contrainte unicite',
    'Quota de provisioning depasse',
]
SUCCESS_MSGS = {
    'ajouter':  'Compte AD/LDAP cree avec succes',
    'modifier': 'Compte mis a jour avec succes',
}
ACTION_MAP = {
    'ajouter':  'CREATE_ACCOUNT',
    'modifier': 'UPDATE_ACCOUNT',
}


def _rdate(start_days_ago: int, end_days_ago: int = 0) -> datetime:
    start = datetime.now() - timedelta(days=start_days_ago)
    delta = timedelta(days=start_days_ago - end_days_ago)
    return start + timedelta(seconds=random.randint(0, max(1, int(delta.total_seconds()))))


def _slug(s: str) -> str:
    return (s.lower()
             .replace(' ', '.')
             .replace('é', 'e').replace('è', 'e').replace('ê', 'e')
             .replace('à', 'a').replace('â', 'a')
             .replace('ù', 'u').replace('û', 'u')
             .replace('î', 'i').replace('ï', 'i')
             .replace('ô', 'o').replace('ç', 'c'))


# ── RH generators ─────────────────────────────────────────────────────────────

def _gen_rh_base() -> pd.DataFrame:
    """Snapshot M-1 : population de base."""
    now  = datetime.now()
    m1   = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    rows = []
    for i in range(N_BASE):
        rows.append({
            'matricule':          f'EMP{str(i + 1001).zfill(5)}',
            'nom':                random.choice(LAST_NAMES).upper(),
            'prenom':             random.choice(FIRST_NAMES),
            'fonction':           random.choice(FUNCTIONS),
            'entite_affectation': random.choice(ENTITIES) if random.random() > 0.02 else '',
            'site':               random.choice(SITES),
            'mois':               m1,
        })
    return pd.DataFrame(rows)


def _gen_rh_current(rh_m1: pd.DataFrame) -> pd.DataFrame:
    """
    Snapshot M dérivé de M-1. Scénarios intra :
      - intra_avec_site     : même entité, site différent
      - intra_avec_fonction : même entité, même site, fonction différente
      - intra_site_et_fonc  : même entité, site ET fonction différents
    """
    now   = datetime.now()
    m_str = now.strftime('%Y-%m')
    n     = len(rh_m1)

    deact_idx = set(random.sample(range(n), k=max(1, int(n * 0.08))))

    rows = []
    for i, (_, emp) in enumerate(rh_m1.iterrows()):
        if i in deact_idx:
            continue

        ent     = emp['entite_affectation']
        site    = emp['site']
        fonction = emp['fonction']
        action  = 'RAS'
        r       = random.random()

        if r < 0.08 and ent:
            # Extra entité + changement de site
            ent    = random.choice([e for e in ENTITIES if e != emp['entite_affectation']])
            site   = random.choice([s for s in SITES   if s != emp['site']])
            action = 'modifier'
        elif r < 0.15 and ent:
            # Extra entité sans changement de site
            ent    = random.choice([e for e in ENTITIES if e != emp['entite_affectation']])
            action = 'modifier'
        elif r < 0.20:
            # Intra avec changement de site uniquement
            site   = random.choice([s for s in SITES if s != emp['site']])
            action = 'modifier'
        elif r < 0.26:
            # Intra avec changement de fonction uniquement (même site)
            fonction = random.choice([f for f in FUNCTIONS if f != emp['fonction']])
            action   = 'modifier'
        elif r < 0.30:
            # Intra avec changement de site ET de fonction
            site     = random.choice([s for s in SITES    if s != emp['site']])
            fonction = random.choice([f for f in FUNCTIONS if f != emp['fonction']])
            action   = 'modifier'

        rows.append({
            'matricule':          emp['matricule'],
            'nom':                emp['nom'],
            'prenom':             emp['prenom'],
            'fonction':           fonction,
            'entite_affectation': ent,
            'site':               site,
            'action':             action,
            'mois':               m_str,
        })

    # Nouveaux arrivants
    n_new = max(1, int(n * 0.10))
    for i in range(n_new):
        rows.append({
            'matricule':          f'EMP{str(n + i + 1001).zfill(5)}',
            'nom':                random.choice(LAST_NAMES).upper(),
            'prenom':             random.choice(FIRST_NAMES),
            'fonction':           random.choice(FUNCTIONS),
            'entite_affectation': random.choice(ENTITIES),
            'site':               random.choice(SITES),
            'action':             'ajouter',
            'mois':               m_str,
        })

    return pd.DataFrame(rows)


# ── AD / LDAP / Logs generators ───────────────────────────────────────────────

def _gen_ad(rh: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # Choisir ~20 % des matricules comme prestataires (email v-...)
    mats = list(rh['matricule'])
    presta_set = set(random.sample(mats, k=max(1, int(len(mats) * 0.20))))

    for _, row in rh.iterrows():
        enabled    = random.random() > 0.04
        last_logon = _rdate(400, 91) if (not enabled or random.random() < 0.10) else _rdate(89, 0)

        dept  = row['entite_affectation']
        title = row['fonction']
        if random.random() < 0.05 and dept:
            dept  = dept + '_ANCIEN'
        if random.random() < 0.05:
            title = title + ' (Ancien)'

        fn = _slug(row['prenom'])
        ln = _slug(row['nom'])
        is_presta = row['matricule'] in presta_set
        # Prestataire : v-prenom.nom@company.ma  |  Agent : prenom.nom@company.ma
        email_prefix = 'v-' if is_presta else ''

        rows.append({
            'employeeID':      row['matricule'],
            'displayName':     f"{row['prenom']} {row['nom']}",
            'department':      dept,
            'title':           title,
            'enabled':         enabled,
            'lastLogon':       last_logon.strftime('%Y-%m-%d'),
            'lockedOut':       random.random() < 0.05,
            'passwordExpired': random.random() < 0.08,
            'mail':            f"{email_prefix}{fn}.{ln}@company.ma" if random.random() > 0.04 else '',
            'timestamp':       _rdate(365, 0).strftime('%Y-%m-%d %H:%M:%S'),
        })
    return pd.DataFrame(rows)


def _gen_ldap(rh: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in rh.iterrows():
        # ~5 % d'employés RH sans compte LDAP (comptes manquants)
        if random.random() < 0.05:
            continue

        fn = _slug(row['prenom'])
        ln = _slug(row['nom'])

        # last_logon : 5 % jamais connecté, 12 % inactif >180j, reste récent
        r_ll = random.random()
        if r_ll < 0.05:
            last_logon = ''
        elif r_ll < 0.17:
            last_logon = _rdate(400, 181).strftime('%Y-%m-%d')
        else:
            last_logon = _rdate(179, 0).strftime('%Y-%m-%d')

        # department : ~7 % incohérent avec RH
        dept = row['entite_affectation']
        if random.random() < 0.07 and dept:
            dept = random.choice([e for e in ENTITIES if e != dept])

        # cn : ~4 % incohérent (nom modifié)
        cn = f"{row['prenom']} {row['nom']}"
        if random.random() < 0.04:
            cn = cn + '_OLD'

        rows.append({
            'uid':         row['matricule'],
            'cn':          cn,
            'mail':        f"{fn}.{ln}@company.ma" if random.random() > 0.05 else '',
            'enabled':     random.random() > 0.03,
            'description': row['fonction'],
            'role':        'admin' if random.random() < 0.06 else 'user',
            'department':  dept,
            'last_logon':  last_logon,
        })

    # ── Comptes orphelins : présents dans LDAP, absents de RH ──
    for i in range(12):
        prenom = random.choice(FIRST_NAMES)
        nom    = random.choice(LAST_NAMES)
        fn2    = _slug(prenom)
        ln2    = _slug(nom)
        rows.append({
            'uid':         f'OLD{str(i + 9001).zfill(5)}',
            'cn':          f"{prenom} {nom.upper()}",
            'mail':        f"{fn2}.{ln2}@company.ma",
            'enabled':     random.random() > 0.30,   # 70 % encore actifs !
            'description': random.choice(FUNCTIONS),
            'role':        'admin' if random.random() < 0.25 else 'user',
            'department':  random.choice(ENTITIES),
            'last_logon':  _rdate(400, 200).strftime('%Y-%m-%d'),
        })

    # ── Doublons mail forcés (3 paires) ────────────────────────
    emp_with_mail = [r for r in rows if r.get('mail') and str(r['uid']).startswith('EMP')]
    for i, src in enumerate(emp_with_mail[:3]):
        prenom2 = random.choice(FIRST_NAMES)
        nom2    = random.choice(LAST_NAMES)
        rows.append({
            'uid':         f'DUP{str(i + 8001).zfill(5)}',
            'cn':          f"{prenom2} {nom2.upper()}",
            'mail':        src['mail'],          # même mail → doublon
            'enabled':     True,
            'description': random.choice(FUNCTIONS),
            'role':        'user',
            'department':  random.choice(ENTITIES),
            'last_logon':  _rdate(30, 0).strftime('%Y-%m-%d'),
        })

    return pd.DataFrame(rows)


def _gen_logs(rh: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in rh.iterrows():
        if row['action'] not in ACTION_MAP:
            continue
        for _ in range(random.randint(1, 4)):
            ok = random.random() > 0.10
            rows.append({
                'date':      _rdate(30, 0).strftime('%Y-%m-%d %H:%M:%S'),
                'matricule': row['matricule'],
                'action':    ACTION_MAP[row['action']],
                'statut':    'success' if ok else 'error',
                'message':   SUCCESS_MSGS[row['action']] if ok else random.choice(ERROR_MSGS),
            })
    df = pd.DataFrame(rows)
    return df.sort_values('date', ascending=False).reset_index(drop=True)


# ── Public API ────────────────────────────────────────────────────────────────

def generate_all(output_dir: str | None = None) -> None:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(output_dir, exist_ok=True)

    print("  Generating RH M-1 (snapshot mois precedent) ...")
    rh_m1 = _gen_rh_base()
    rh_m1.to_csv(os.path.join(output_dir, 'rh_M1.csv'), index=False, encoding='utf-8-sig')

    print("  Generating RH M (snapshot mois courant) ...")
    rh_m = _gen_rh_current(rh_m1)
    rh_m.to_csv(os.path.join(output_dir, 'rh_M.csv'), index=False, encoding='utf-8-sig')

    print("  Generating AD ...")
    ad = _gen_ad(rh_m)
    ad.to_csv(os.path.join(output_dir, 'ad.csv'), index=False, encoding='utf-8-sig')

    print("  Generating LDAP ...")
    ldap = _gen_ldap(rh_m)
    ldap.to_csv(os.path.join(output_dir, 'ldap.csv'), index=False, encoding='utf-8-sig')

    print("  Generating Logs ...")
    logs = _gen_logs(rh_m)
    logs.to_csv(os.path.join(output_dir, 'logs.csv'), index=False, encoding='utf-8-sig')

    print(f"  Done - M-1:{len(rh_m1)} emp, M:{len(rh_m)} emp, {len(logs)} logs -> {output_dir}")


if __name__ == '__main__':
    print("IAM Dashboard - generating sample data ...")
    generate_all()
