"""
Générateur de synthèses PDF — IAM Dashboard.
Design amélioré : page de couverture, KPI cards, tableaux stylisés.
"""
from datetime import datetime
from io import BytesIO
import os
import pandas as pd
from fpdf import FPDF

# ── Polices ───────────────────────────────────────────────────────────────────
_FONT_DIR  = r"C:\Windows\Fonts"
_FONTS = {
    "reg":   os.path.join(_FONT_DIR, "arial.ttf"),
    "bold":  os.path.join(_FONT_DIR, "arialbd.ttf"),
    "it":    os.path.join(_FONT_DIR, "ariali.ttf"),
}
_USE_TTF = all(os.path.exists(p) for p in _FONTS.values())

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "primary":    (13,   33,  55),   # bleu nuit
    "accent":     (25,  118, 210),   # bleu vif
    "accent_lt":  (227, 242, 253),   # bleu très clair
    "green":      (46,  125,  50),
    "green_lt":   (232, 245, 233),
    "red":        (198,  40,  40),
    "red_lt":     (255, 235, 238),
    "orange":     (230, 111,   0),
    "orange_lt":  (255, 243, 224),
    "purple":     (106,  27, 154),
    "purple_lt":  (243, 229, 245),
    "grey":       (96,  125, 139),
    "grey_lt":    (245, 247, 250),
    "grey_mid":   (207, 216, 220),
    "white":      (255, 255, 255),
    "black":      (33,   33,  33),
    "text_muted": (117, 117, 117),
}

PW = 297   # A4 landscape width mm
PH = 210   # A4 landscape height mm
ML = 14    # margin left/right
MT = 14    # margin top (after header)


def _c(name):
    return C[name]


# ══════════════════════════════════════════════════════════════════════════════
# Classe de base
# ══════════════════════════════════════════════════════════════════════════════
class _PDF(FPDF):

    def __init__(self, doc_type: str, titre: str, meta: dict):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(ML, 30, ML)

        # ── Polices ──────────────────────────────────────────────────────────
        if _USE_TTF:
            self.add_font("F",  "",  _FONTS["reg"],  uni=True)
            self.add_font("F",  "B", _FONTS["bold"], uni=True)
            self.add_font("F",  "I", _FONTS["it"],   uni=True)
            self._fn = "F"
        else:
            self._fn = "Helvetica"

        _EMOJI_MAP = {
            "✅": "OK",  "❌": "--",  "⚠️": "!",  "⚠": "!",
            "🔐": "[IAM]", "🟢": "[OK]", "🔴": "[KO]", "🟡": "[!]",
            "➕": "+",  "⬇": "v",  "📄": "[PDF]", "🔄": "[refresh]",
        }

        def _clean(s: str) -> str:
            s = str(s)
            for em, repl in _EMOJI_MAP.items():
                s = s.replace(em, repl)
            if _USE_TTF:
                return s
            return (s
                    .replace("↔","<>").replace("→","->").replace("←","<-")
                    .replace("—","-").replace("–","-").replace("·",".")
                    .replace("≠","!=").replace("≈","~"))

        self._c  = _clean
        self._doc_type = _clean(doc_type)
        self._titre    = _clean(titre)
        self._meta     = {_clean(k): _clean(v) for k, v in meta.items()}
        self._now      = datetime.now()
        self._now_str  = self._now.strftime("%d/%m/%Y  %H:%M")

        # ── Page de couverture ────────────────────────────────────────────────
        self._cover_page()

    # ─────────────────────────────────────────────────────────────────────────
    # PAGE DE COUVERTURE
    # ─────────────────────────────────────────────────────────────────────────
    def _cover_page(self):
        self.add_page()
        self.set_auto_page_break(False)

        # Fond complet
        self._fill(0, 0, PW, PH, "primary")

        # Bande décorative droite
        self._fill(PW - 40, 0, 40, PH, "accent")

        # Bande décorative verticale fine
        self._fill(PW - 44, 0, 2, PH, C["accent_lt"])

        # Bloc blanc central
        self._fill(ML, 35, PW - 70, 130, "white")

        # Liseré gauche coloré
        self._fill(ML, 35, 4, 130, "accent")

        # Titre principal
        self.set_xy(ML + 10, 44)
        self.set_font(self._fn, "B", 28)
        self.set_text_color(*_c("primary"))
        self.multi_cell(PW - 85, 12, self._titre, ln=1)

        # Sous-titre type doc
        self.set_xy(ML + 10, self.get_y() + 2)
        self.set_font(self._fn, "", 13)
        self.set_text_color(*_c("accent"))
        self.cell(PW - 85, 7, self._doc_type, ln=1)

        # Ligne séparatrice
        self._hline(ML + 10, self.get_y() + 4, PW - 75, _c("grey_mid"), 0.3)

        # Métadonnées
        y_meta = self.get_y() + 8
        for k, v in self._meta.items():
            self.set_xy(ML + 10, y_meta)
            self.set_font(self._fn, "B", 8)
            self.set_text_color(*_c("grey"))
            self.cell(35, 5, k.upper(), ln=0)
            self.set_font(self._fn, "", 9)
            self.set_text_color(*_c("black"))
            self.cell(100, 5, v, ln=1)
            y_meta += 6

        # Date en bas du bloc
        self.set_xy(ML + 10, 148)
        self.set_font(self._fn, "I", 8)
        self.set_text_color(*_c("text_muted"))
        self.cell(PW - 85, 5, f"Généré le  {self._now_str}", ln=0)

        # Texte vertical dans la bande droite
        self.set_xy(PW - 37, 40)
        self.set_font(self._fn, "B", 9)
        self.set_text_color(*_c("white"))
        self.cell(30, 6, "IAM Dashboard", align='C', ln=1)
        self.set_xy(PW - 37, 48)
        self.set_font(self._fn, "", 8)
        self.cell(30, 5, "Supervision", align='C', ln=1)
        self.set_xy(PW - 37, 54)
        self.cell(30, 5, "Identity &", align='C', ln=1)
        self.set_xy(PW - 37, 60)
        self.cell(30, 5, "Access Mgmt", align='C', ln=1)

        self.set_auto_page_break(True, margin=18)

    # ─────────────────────────────────────────────────────────────────────────
    # HEADER / FOOTER automatiques
    # ─────────────────────────────────────────────────────────────────────────
    def header(self):
        if self.page_no() == 1:
            return
        # Bande supérieure
        self._fill(0, 0, PW, 14, "primary")
        # Accent ligne fine en bas du header
        self._fill(0, 14, PW, 1, "accent")

        self.set_xy(ML, 2)
        self.set_font(self._fn, "B", 9)
        self.set_text_color(*_c("white"))
        self.cell(140, 6, self._titre, ln=0)

        self.set_font(self._fn, "", 7)
        self.set_text_color(*_c("accent_lt"))
        self.set_xy(180, 2)
        self.cell(100, 6, f"IAM Dashboard  |  {self._now_str}", align='R', ln=1)

        self.set_xy(ML, 3)
        self.set_font(self._fn, "I", 7)
        self.set_text_color(_c("accent_lt")[0], _c("accent_lt")[1], _c("accent_lt")[2])

    def footer(self):
        if self.page_no() == 1:
            return
        self._fill(0, PH - 10, PW, 10, "primary")
        self._fill(0, PH - 10, PW, 1, "accent")

        self.set_xy(ML, PH - 8)
        self.set_font(self._fn, "", 7)
        self.set_text_color(*_c("grey_mid"))
        self.cell(140, 5, self._c("IAM Dashboard  —  Synthèse confidentielle"), ln=0)

        self.set_xy(200, PH - 8)
        self.set_font(self._fn, "B", 8)
        self.set_text_color(*_c("accent_lt"))
        self.cell(80, 5, f"Page  {self.page_no()}", align='R')

    # ─────────────────────────────────────────────────────────────────────────
    # PRIMITIVES
    # ─────────────────────────────────────────────────────────────────────────
    def _fill(self, x, y, w, h, color):
        if isinstance(color, str):
            color = _c(color)
        self.set_fill_color(*color)
        self.rect(x, y, w, h, 'F')

    def _hline(self, x, y, w, color=None, lw=0.2):
        color = color or _c("grey_mid")
        self.set_draw_color(*color)
        self.set_line_width(lw)
        self.line(x, y, x + w, y)

    def new_content_page(self):
        self.add_page()
        self.set_xy(ML, 18)

    # ─────────────────────────────────────────────────────────────────────────
    # COMPOSANTS DESIGN
    # ─────────────────────────────────────────────────────────────────────────

    def section_title(self, text: str, color_key: str = "accent"):
        """Titre de section avec liseré gauche et fond très léger."""
        color  = _c(color_key)
        lt_key = color_key + "_lt"
        bg     = _c(lt_key) if lt_key in C else _c("grey_lt")

        h = 8
        y = self.get_y()
        x = ML

        # Fond clair
        self._fill(x, y, PW - 2*ML, h, bg)
        # Liseré gauche
        self._fill(x, y, 3, h, color_key)

        self.set_xy(x + 6, y + 1)
        self.set_font(self._fn, "B", 9)
        self.set_text_color(*color)
        self.cell(PW - 2*ML - 6, h - 2, self._c(text), ln=1)
        self.set_text_color(*_c("black"))
        self.ln(3)

    def kpi_cards(self, items: list):
        """items = [(label, value, color_key), ...]  — max 5 par ligne."""
        n   = len(items)
        cw  = (PW - 2*ML) / n
        x0  = ML
        y0  = self.get_y()
        ch  = 20   # card height

        for i, (label, value, ck) in enumerate(items):
            x   = x0 + i * cw
            col = _c(ck)
            lt  = _c(ck + "_lt") if (ck + "_lt") in C else _c("grey_lt")

            # Fond de la card
            self._fill(x, y0, cw - 1.5, ch, lt)
            # Liseré haut
            self._fill(x, y0, cw - 1.5, 2.5, ck)

            # Valeur
            self.set_xy(x, y0 + 3)
            self.set_font(self._fn, "B", 17)
            self.set_text_color(*col)
            self.cell(cw - 1.5, 9, str(value), align='C', ln=0)

            # Label
            self.set_xy(x, y0 + 12)
            self.set_font(self._fn, "", 7)
            self.set_text_color(*_c("text_muted"))
            self.cell(cw - 1.5, 6, self._c(label), align='C', ln=0)

        self.set_xy(x0, y0 + ch + 3)
        self.set_text_color(*_c("black"))
        self.ln(1)

    def scorecard(self, items: list):
        """Badges scorecard A–F avec valeur proéminente."""
        n   = len(items)
        cw  = (PW - 2*ML) / n
        x0  = ML
        y0  = self.get_y()
        ch  = 22

        for i, (label, value, ck) in enumerate(items):
            x   = x0 + i * cw
            col = _c(ck)
            lt  = _c(ck + "_lt") if (ck + "_lt") in C else _c("grey_lt")

            # Fond blanc avec liseré couleur en bas
            self._fill(x, y0, cw - 1.5, ch, "white")
            # Bord
            self.set_draw_color(*_c("grey_mid"))
            self.set_line_width(0.2)
            self.rect(x, y0, cw - 1.5, ch)
            # Barre du bas
            self._fill(x, y0 + ch - 3, cw - 1.5, 3, ck)

            # Valeur
            self.set_xy(x, y0 + 2)
            self.set_font(self._fn, "B", 18)
            self.set_text_color(*col)
            self.cell(cw - 1.5, 11, str(value), align='C', ln=0)

            # Label
            self.set_xy(x, y0 + 13)
            self.set_font(self._fn, "", 7)
            self.set_text_color(*_c("text_muted"))
            self.cell(cw - 1.5, 5, self._c(label), align='C', ln=0)

        self.set_xy(x0, y0 + ch + 4)
        self.set_text_color(*_c("black"))
        self.ln(1)

    def alert_badge(self, niveau: str, msg: str):
        ck_map = {'CRITIQUE': 'red', 'IMPORTANT': 'orange', 'INFO': 'accent'}
        ck  = ck_map.get(niveau, 'grey')
        col = _c(ck)
        lt  = _c(ck + "_lt") if (ck + "_lt") in C else _c("grey_lt")

        y = self.get_y()
        w = PW - 2 * ML

        self._fill(ML, y, w, 7, lt)
        self._fill(ML, y, 2.5, 7, ck)

        # Badge niveau
        self._fill(ML + 4, y + 1.5, 22, 4, ck)
        self.set_xy(ML + 4, y + 1.5)
        self.set_font(self._fn, "B", 6.5)
        self.set_text_color(*_c("white"))
        self.cell(22, 4, niveau, align='C', ln=0)

        # Message
        self.set_xy(ML + 29, y + 1.5)
        self.set_font(self._fn, "", 8)
        self.set_text_color(*_c("black"))
        self.cell(w - 32, 4, self._c(msg), ln=1)
        self.ln(1)

    def data_table(self, headers: list, rows: list, col_widths: list = None,
                   accent_key: str = "accent"):
        n = len(headers)
        if not col_widths:
            avail = PW - 2 * ML
            col_widths = [avail / n] * n

        col = _c(accent_key)

        # ── En-tête ───────────────────────────────────────────────────────────
        self._fill(ML, self.get_y(), sum(col_widths), 7, accent_key)
        self.set_font(self._fn, "B", 7.5)
        self.set_text_color(*_c("white"))
        for h, w in zip(headers, col_widths):
            self.cell(w, 7, f"  {self._c(h)}", fill=False, border=0, ln=0)
        self.ln()

        # ── Lignes ────────────────────────────────────────────────────────────
        self.set_font(self._fn, "", 7)
        for idx, row in enumerate(rows):
            if self.get_y() > PH - 25:
                self.add_page()
                self.set_xy(ML, 18)
                # Répéter l'en-tête
                self._fill(ML, self.get_y(), sum(col_widths), 7, accent_key)
                self.set_font(self._fn, "B", 7.5)
                self.set_text_color(*_c("white"))
                for h, w in zip(headers, col_widths):
                    self.cell(w, 7, f"  {self._c(h)}", fill=False, border=0, ln=0)
                self.ln()
                self.set_font(self._fn, "", 7)

            is_even = idx % 2 == 0
            bg = _c("grey_lt") if is_even else _c("white")
            self.set_fill_color(*bg)
            self.set_text_color(*_c("black"))

            for val, w in zip(row, col_widths):
                txt = str(val)[:45]
                self.cell(w, 5.5, f"  {self._c(txt)}", fill=True, border=0, ln=0)
            self.ln()

        # Ligne de fermeture
        self._hline(ML, self.get_y(), sum(col_widths), _c("grey_mid"), 0.3)
        self.ln(4)

    def divider(self, label: str = ""):
        self.ln(2)
        self._hline(ML, self.get_y(), PW - 2*ML, _c("grey_mid"), 0.2)
        if label:
            self.set_xy(ML + 4, self.get_y() - 1)
            self.set_font(self._fn, "I", 7)
            self.set_text_color(*_c("text_muted"))
            self.cell(60, 4, self._c(label))
        self.ln(3)

    def info_box(self, text: str, color_key: str = "accent"):
        lt = _c(color_key + "_lt") if (color_key + "_lt") in C else _c("grey_lt")
        y = self.get_y()
        self._fill(ML, y, PW - 2*ML, 8, lt)
        self._fill(ML, y, 2.5, 8, color_key)
        self.set_xy(ML + 5, y + 1.5)
        self.set_font(self._fn, "I", 8)
        self.set_text_color(*_c("text_muted"))
        self.multi_cell(PW - 2*ML - 8, 4.5, self._c(text))
        self.ln(2)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Synthèse Vue Globale
# ══════════════════════════════════════════════════════════════════════════════
def pdf_synthese_globale(kpis: dict, rh: pd.DataFrame, now: datetime) -> bytes:
    m_label = rh['mois'].iloc[0] if not rh.empty else '-'

    pdf = _PDF(
        doc_type="Synthèse Mensuelle — Vue Globale",
        titre="IAM Dashboard — Vue Globale",
        meta={
            "Mois de référence" : m_label,
            "Effectif total"    : f"{len(rh)} employés",
            "Source"            : "RH · Active Directory · LDAP",
            "Généré le"         : now.strftime("%d/%m/%Y à %H:%M"),
        }
    )

    pdf.new_content_page()

    # ── Indicateurs principaux ────────────────────────────────────────────────
    pdf.section_title("Indicateurs Utilisateurs", "accent")
    pdf.kpi_cards([
        ("Total Utilisateurs",  kpis['total_users'],            "accent"),
        ("Comptes Actifs AD",   kpis['active_users'],           "green"),
        ("Comptes Inactifs",    kpis['inactive_users'],         "grey"),
        ("Nouveaux Comptes",    kpis['new_accounts'],           "purple"),
        ("Taux Automatisation", f"{kpis['automation_rate']} %", "orange"),
    ])

    pdf.section_title("Provisioning — Actions du mois", "green")
    pdf.kpi_cards([
        ("Créations",      kpis['created'],       "green"),
        ("Modifications",  kpis['modified'],      "accent"),
        ("Désactivations", kpis['disabled'],      "red"),
        ("Logs succès",    kpis['log_success'],   "green"),
        ("Logs erreurs",   kpis['log_error'],     "red"),
    ])

    pdf.section_title("Sécurité — Alertes rapides", "red")
    pdf.kpi_cards([
        ("Comptes bloqués",    kpis['locked_accounts'], "red"),
        ("MDP expirés",        kpis['pwd_expired'],     "orange"),
        ("Inactifs > 90 j",    kpis['inactive_90d'],    "purple"),
        ("Sans mail",          kpis['no_mail'],         "grey"),
        ("Incohérences RH/AD", kpis['inconsistencies'], "orange"),
    ])

    pdf.section_title("Mobilité RH — M vs M-1", "purple")
    pdf.kpi_cards([
        ("Total mobilités",  kpis['total_mobility'],      "accent"),
        ("Extra + site",     kpis['extra_avec_site'],     "red"),
        ("Extra sans site",  kpis['extra_sans_site'],     "orange"),
        ("Intra + site",     kpis['intra_avec_site'],     "purple"),
        ("Intra + fonction", kpis['intra_avec_fonction'], "grey"),
    ])

    pdf.divider()

    # ── Répartition actions ───────────────────────────────────────────────────
    pdf.section_title("Répartition des actions RH", "accent")
    act = rh['action'].value_counts().reset_index()
    act.columns = ['Action', 'Nombre']
    act['%'] = (act['Nombre'] / len(rh) * 100).round(1).astype(str) + ' %'
    pdf.data_table(['Action', 'Nombre', 'Pourcentage'], act.values.tolist(),
                   [70, 55, 55])

    # ── Effectifs par entité ──────────────────────────────────────────────────
    pdf.section_title("Effectifs par entité", "accent")
    ent = (rh[rh['entite_affectation'] != '']
           .groupby('entite_affectation')['matricule'].count()
           .reset_index(name='Effectif')
           .sort_values('Effectif', ascending=False))
    ent.columns = ['Entité', 'Effectif']
    ent['%'] = (ent['Effectif'] / len(rh) * 100).round(1).astype(str) + ' %'
    pdf.data_table(['Entité', 'Effectif', '%'], ent.values.tolist(),
                   [100, 50, 50])

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 2. Synthèse Analyse LDAP
# ══════════════════════════════════════════════════════════════════════════════
def pdf_synthese_ldap(r: dict, rh: pd.DataFrame, ldap: pd.DataFrame, now: datetime) -> bytes:
    m_label    = rh['mois'].iloc[0] if not rh.empty else '-'
    n_inco     = r['n_inco_name'] + r['n_inco_status'] + r['n_inco_dept']
    total_crit = r['n_orphans'] + r['n_to_deactivate'] + r['n_inactive_admins']
    total_imp  = r['n_missing'] + r['n_dup_mail'] + r['n_dup_cn']

    pdf = _PDF(
        doc_type="Synthèse Analyse — LDAP vs RH",
        titre="Analyse LDAP vs RH",
        meta={
            "Mois de référence" : m_label,
            "Employés RH"       : f"{len(rh)}",
            "Comptes LDAP"      : f"{len(ldap)}",
            "Clé de jointure"   : "matricule = uid",
            "Généré le"         : now.strftime("%d/%m/%Y à %H:%M"),
        }
    )

    pdf.new_content_page()

    # ── Scorecard A-F ────────────────────────────────────────────────────────
    pdf.section_title("Scorecard Global — Sections A à F", "accent")
    pdf.scorecard([
        ("A  Orphelins",    r['n_orphans'],                  "red"),
        ("B  A désactiver", r['n_to_deactivate'],            "red"),
        ("C  Manquants",    r['n_missing'],                  "orange"),
        ("D  Admins",       r['n_admins'],                   "purple"),
        ("E  Doublons",     r['n_dup_cn'] + r['n_dup_mail'], "orange"),
        ("F  Incoherences", n_inco,                          "accent"),
    ])

    # ── Alertes ───────────────────────────────────────────────────────────────
    pdf.section_title("Niveau de criticité global", "red")
    pdf.alert_badge("CRITIQUE",  f"{total_crit} probleme(s) a traiter en priorité — orphelins actifs, désactivations, admins inactifs LDAP")
    pdf.alert_badge("IMPORTANT", f"{total_imp} element(s) a vérifier — comptes manquants dans LDAP, doublons CN/mail")
    pdf.alert_badge("INFO",      f"{n_inco} incoherence(s) a corriger — noms, statuts, départements désynchronisés")
    pdf.ln(3)

    # ── KPIs B ────────────────────────────────────────────────────────────────
    pdf.section_title("B — Comptes à désactiver (détail)", "orange")
    pdf.kpi_cards([
        ("B1  Inactifs > 180 j",  r['n_b1'],            "orange"),
        ("B2  Employes sortis",   r['n_b2'],            "purple"),
        ("Total à désactiver",    r['n_to_deactivate'], "red"),
    ])

    # ── KPIs D ────────────────────────────────────────────────────────────────
    pdf.section_title("D — Comptes à risque (détail)", "purple")
    pdf.kpi_cards([
        ("Admins total",          r['n_admins'],          "purple"),
        ("Admins inactifs >180j", r['n_inactive_admins'], "red"),
        ("Sans last_logon",       r['n_no_login'],        "orange"),
    ])

    # ── KPIs F ────────────────────────────────────────────────────────────────
    pdf.section_title("F — Incohérences RH vs LDAP (détail)", "accent")
    pdf.kpi_cards([
        ("F1  Noms",        r['n_inco_name'],   "red"),
        ("F2  Statuts",     r['n_inco_status'], "orange"),
        ("F3  Departements",r['n_inco_dept'],   "accent"),
    ])

    pdf.divider()

    # ── Tableau orphelins actifs ──────────────────────────────────────────────
    df_oa = r['a_orphans'][r['a_orphans']['enabled'].astype(bool)]
    if not df_oa.empty:
        pdf.section_title(f"A — Orphelins actifs ({len(df_oa)} compte(s))", "red")
        pdf.info_box("Comptes présents dans LDAP, absents du fichier RH, et encore actifs — accès non autorisé potentiel.", "red")
        cols = [c for c in ['uid','cn','mail','role','department','last_logon'] if c in df_oa.columns]
        rows = df_oa[cols].head(20).fillna('-').astype(str).values.tolist()
        widths = [30, 45, 60, 20, 40, 30][:len(cols)]
        pdf.data_table(cols, rows, widths, "red")

    # ── Tableau admins inactifs ───────────────────────────────────────────────
    if not r['d_inactive_admins'].empty:
        pdf.section_title(f"D — Admins LDAP inactifs >180j ({r['n_inactive_admins']} compte(s))", "purple")
        pdf.info_box("Comptes avec droits admin et aucune connexion depuis plus de 180 jours — accès privilégié dormant.", "purple")
        cols = [c for c in ['uid','cn','mail','last_logon','department'] if c in r['d_inactive_admins'].columns]
        rows = r['d_inactive_admins'][cols].head(20).fillna('-').astype(str).values.tolist()
        widths = [35, 50, 60, 35, 45][:len(cols)]
        pdf.data_table(cols, rows, widths, "purple")

    # ── Tableau incohérences noms ─────────────────────────────────────────────
    if not r['f1_name'].empty:
        pdf.section_title(f"F1 — Noms incohérents ({r['n_inco_name']} cas)", "orange")
        rows = r['f1_name'].head(20).fillna('-').astype(str).values.tolist()
        hdrs = list(r['f1_name'].columns)
        pdf.data_table(hdrs, rows, accent_key="orange")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# 3. Synthèse Analyse AD
# ══════════════════════════════════════════════════════════════════════════════
def pdf_synthese_ad(r: dict, rh: pd.DataFrame, ad: pd.DataFrame, now: datetime) -> bytes:
    m_label    = rh['mois'].iloc[0] if not rh.empty else '-'
    n_inco     = r['n_inco_name'] + r['n_inco_status'] + r['n_inco_dept'] + r['n_inco_title']
    total_crit = r['n_orphans'] + r['n_to_deactivate'] + r['n_locked']
    total_imp  = r['n_missing'] + r['n_dup_mail'] + r['n_pwd_expired']

    pdf = _PDF(
        doc_type="Synthèse Analyse — RH vs Active Directory",
        titre="Analyse RH vs Active Directory",
        meta={
            "Mois de référence" : m_label,
            "Employés RH"       : f"{len(rh)}",
            "Comptes AD"        : f"{len(ad)}",
            "Clé de jointure"   : "matricule = employeeID",
            "Activité"          : "lastLogon  |  Création : timestamp",
            "Généré le"         : now.strftime("%d/%m/%Y à %H:%M"),
        }
    )

    pdf.new_content_page()

    # ── Scorecard A-F ────────────────────────────────────────────────────────
    pdf.section_title("Scorecard Global — Sections A à F", "accent")
    pdf.scorecard([
        ("A  Orphelins",    r['n_orphans'],                  "red"),
        ("B  A désactiver", r['n_to_deactivate'],            "red"),
        ("C  Manquants",    r['n_missing'],                  "orange"),
        ("D  Risque",       r['n_locked']+r['n_pwd_expired'],"red"),
        ("E  Doublons",     r['n_dup_mail'],                 "orange"),
        ("F  Incoherences", n_inco,                          "accent"),
    ])

    # ── Alertes ───────────────────────────────────────────────────────────────
    pdf.section_title("Niveau de criticité global", "red")
    pdf.alert_badge("CRITIQUE",  f"{total_crit} probleme(s) en priorité — orphelins AD, désactivations, comptes bloqués")
    pdf.alert_badge("IMPORTANT", f"{total_imp} element(s) a vérifier — manquants dans AD, MDP expirés, doublons mail")
    pdf.alert_badge("INFO",      f"{n_inco} incoherence(s) — displayName, statut, département, titre/fonction")
    pdf.ln(3)

    # ── Activité lastLogon vs timestamp ───────────────────────────────────────
    pdf.section_title("Activité AD — lastLogon vs timestamp", "orange")
    pdf.kpi_cards([
        ("Inactifs > 90 j",      r['n_inactive_90'], "orange"),
        ("Inactifs > 180 j",     r['n_b1'],          "red"),
        ("Jamais utilisés (D4)", r['n_never_used'],  "purple"),
        ("Comptes bloqués",      r['n_locked'],      "red"),
        ("MDP expirés actifs",   r['n_pwd_expired'], "orange"),
    ])

    # ── KPIs D ────────────────────────────────────────────────────────────────
    pdf.section_title("D — Risques AD (détail)", "red")
    pdf.kpi_cards([
        ("D1  Bloques",          r['n_locked'],      "red"),
        ("D2  MDP expires",      r['n_pwd_expired'], "orange"),
        ("D3  Inactifs > 90 j",  r['n_inactive_90'], "orange"),
        ("D4  Jamais utilises",  r['n_never_used'],  "purple"),
    ])

    # ── KPIs F ────────────────────────────────────────────────────────────────
    pdf.section_title("F — Incohérences RH vs AD (détail)", "accent")
    pdf.kpi_cards([
        ("F1  DisplayName",   r['n_inco_name'],   "red"),
        ("F2  Statut",        r['n_inco_status'], "orange"),
        ("F3  Departement",   r['n_inco_dept'],   "accent"),
        ("F4  Titre/Fonction",r['n_inco_title'],  "purple"),
    ])

    pdf.divider()

    # ── Tableau comptes bloqués ───────────────────────────────────────────────
    if not r['d_locked'].empty:
        pdf.section_title(f"D1 — Comptes bloqués ({r['n_locked']} compte(s))", "red")
        pdf.info_box("lockedOut = True — Intervention immédiate requise pour débloquer ces comptes.", "red")
        cols = [c for c in ['employeeID','displayName','department','lastLogon','timestamp'] if c in r['d_locked'].columns]
        rows = r['d_locked'][cols].head(20).fillna('-').astype(str).values.tolist()
        widths = [30, 55, 45, 35, 35][:len(cols)]
        pdf.data_table(cols, rows, widths, "red")

    # ── Tableau jamais utilisés ───────────────────────────────────────────────
    if not r['d_never_used'].empty:
        pdf.section_title(f"D4 — Jamais utilisés depuis création ({r['n_never_used']} compte(s))", "purple")
        pdf.info_box("lastLogon absent ou égal au timestamp de création — compte actif sans aucune utilisation réelle.", "purple")
        cols = [c for c in ['employeeID','displayName','department','timestamp','lastLogon'] if c in r['d_never_used'].columns]
        rows = r['d_never_used'][cols].head(20).fillna('-').astype(str).values.tolist()
        widths = [30, 55, 45, 35, 35][:len(cols)]
        pdf.data_table(cols, rows, widths, "purple")

    # ── Tableau incohérences statut ───────────────────────────────────────────
    if not r['f2_status'].empty:
        pdf.section_title(f"F2 — Statuts incohérents ({r['n_inco_status']} cas)", "orange")
        rows = r['f2_status'].head(20).fillna('-').astype(str).values.tolist()
        hdrs = list(r['f2_status'].columns)
        pdf.data_table(hdrs, rows, accent_key="orange")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
