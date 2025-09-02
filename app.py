import os
import re
import pandas as pd
import numpy as np
import streamlit as st
import altair as alt

st.set_page_config(page_title="NMF — Suivi", layout="wide")

# --- Logo du club ---
LOGO_PATH = os.path.join(os.path.dirname(__file__), "logo_nmf.png")
if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=200)
else:
    st.warning("Logo introuvable : vérifie le fichier 'logo_nmf.png'")

st.title("Nantes Métropole Futsal — Suivi des performances")

# ---------------- Google Sheets parser ----------------
@st.cache_data(ttl="10m")  # Cache pendant 10 minutes
def parse_google_sheet():
    SHEET_ID = "1-QCywSqXboG2k1xLmaX2eRy7MWXzwcKoEPfIHbbEIY8"
    
    all_records = []
    int_re = re.compile(r'(\d+)')
    day_names = {"lundi":1,"mardi":2,"mercredi":3,"jeudi":4,"vendredi":5,"samedi":6,"dimanche":7}
    
    # Lire toutes les feuilles - celles sans données seront automatiquement ignorées
    sheets = [
        ("Août", 0),
        ("Septembre", 1815364140),
        ("Octobre", 2065545828),
        ("Novembre", 2055534384),
        ("Décembre", 2028758753),
        ("Janvier", 228471660),
        ("Février", 1003146032),
        ("Mars", 1342797580),
        ("Avril", 1812433009),
        ("Mai", 549449988),
        ("Juin", 557016746)
    ]
    
    for sheet_name, gid in sheets:
        try:
            # URL pour lire une feuille spécifique en CSV avec le bon GID
            sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
            
            # Lire les données depuis Google Sheets
            raw = pd.read_csv(sheet_url, header=None)
            
            if raw.empty:
                continue
                
            nrows, ncols = raw.shape

            # Détection des lignes jour / jeu (même logique qu'avant)
            candidate_day_scores = []
            for r in range(min(6, nrows)):
                row_vals = raw.iloc[r, 1:].astype(str).fillna("").str.strip().str.lower().tolist()
                score = sum(1 for v in row_vals if v in day_names)
                candidate_day_scores.append((r, score))
            row_jours = max(candidate_day_scores, key=lambda x: x[1])[0] if candidate_day_scores else 0

            candidate_num_scores = []
            for r in range(row_jours + 1, min(row_jours + 6, nrows)):
                row_vals = raw.iloc[r, 1:].astype(str).fillna("").str.strip().tolist()
                score = sum(1 for v in row_vals if int_re.search(str(v)))
                candidate_num_scores.append((r, score))
            row_jeux = max(candidate_num_scores, key=lambda x: x[1])[0] if candidate_num_scores else min(row_jours + 1, nrows-1)

            if row_jours < nrows and row_jeux < nrows:
                jours_series = raw.iloc[row_jours].ffill().fillna("Séance inconnue").astype(str).str.strip()
                jeux_series = raw.iloc[row_jeux].astype(str).fillna("").str.strip()

                # Lecture des joueurs/gardiens
                for r in range(row_jeux + 1, nrows):
                    if r >= len(raw):
                        continue
                        
                    joueur_cell = raw.iat[r, 0] if ncols > 0 else None
                    poste_cell = raw.iat[r, 1] if ncols > 1 else None
                    
                    if pd.isna(joueur_cell) or str(joueur_cell).strip() == "":
                        continue
                    
                    joueur_name = str(joueur_cell).strip()
                    poste = str(poste_cell).strip() if not pd.isna(poste_cell) else "Joueur"
                for r in range(row_jeux + 1, nrows):
                    if r >= len(raw):
                        continue
                        
                    joueur_cell = raw.iat[r, 0] if ncols > 0 else None
                    poste_cell = raw.iat[r, 1] if ncols > 1 else None
                    
                    if pd.isna(joueur_cell) or str(joueur_cell).strip() == "":
                        continue
                    
                    joueur_name = str(joueur_cell).strip()
                    poste = str(poste_cell).strip() if not pd.isna(poste_cell) else "Joueur"
                    
                    for c in range(2, ncols):
                        if c >= len(raw.columns):
                            continue
                            
                        raw_val = raw.iat[r, c]
                        if pd.isna(raw_val) or str(raw_val).strip() == "":
                            continue
                            
                        jeu_cell = str(jeux_series.iloc[c]).strip() if c < len(jeux_series) else ""
                        m = int_re.search(jeu_cell)
                        jeu_num = int(m.group(1)) if m else c-1
                        jour_name = str(jours_series.iloc[c]).strip() if c < len(jours_series) else "Séance inconnue"
                        jour_index = day_names.get(jour_name.lower(), 0)
                        
                        # Calcul de semaine amélioré
                        # Pour chaque jour, on regarde la colonne pour déterminer la semaine
                        if jour_index > 0:
                            # Calcul basé sur la position de la colonne
                            if c <= 7:  # Colonnes C à I (première semaine)
                                semaine = 1
                            elif c <= 13:  # Colonnes J à P (deuxième semaine)  
                                semaine = 2
                            elif c <= 19:  # Colonnes Q à W (troisième semaine)
                                semaine = 3
                            else:  # Colonnes suivantes
                                semaine = 4
                        else:
                            semaine = 1

                        if poste.lower() != "gardien":
                            val_str = str(raw_val).strip().upper()
                            
                            if val_str not in ("V","D","N"):  # Ajouter "N" pour match nul
                                continue
                            
                            # Créer l'enregistrement avec les nouvelles variables
                            all_records.append({
                                "Mois": str(sheet_name),
                                "Joueur": joueur_name,
                                "Seance": jour_name,
                                "Jour_index": jour_index,
                                "Semaine": semaine,
                                "Jeu": int(jeu_num),
                                "Resultat": val_str,
                                "Victoire": 1 if val_str=="V" else 0,
                                "Défaite": 1 if val_str=="D" else 0,
                                "Nul": 1 if val_str=="N" else 0,  # Nouvelle colonne pour les nuls
                                "Postes": poste,
                                "Buts_encaisses": np.nan
                            })
                        else:
                            try:
                                buts = float(raw_val)
                            except:
                                buts = np.nan
                            all_records.append({
                                "Mois": str(sheet_name),
                                "Joueur": joueur_name,
                                "Seance": jour_name,
                                "Jour_index": jour_index,
                                "Semaine": semaine,
                                "Jeu": int(jeu_num),
                                "Resultat": np.nan,
                                "Victoire": np.nan,
                                "Défaite": np.nan,
                                "Nul": np.nan,  # Ajouter aussi pour les gardiens
                                "Postes": poste,
                                "Buts_encaisses": buts
                            })
                            
        except Exception as e:
            st.error(f"Erreur lecture feuille {sheet_name}: {str(e)}")
            continue
    
    df = pd.DataFrame(all_records, columns=["Mois","Joueur","Seance","Jour_index","Semaine","Jeu","Resultat","Victoire","Défaite","Nul","Postes","Buts_encaisses"])
    if not df.empty:
        df["Jeu"] = df["Jeu"].astype(int)
        df["Seance"] = df["Seance"].fillna("Séance inconnue").astype(str)
        df["Mois"] = df["Mois"].astype(str)
        df["Postes"] = df["Postes"].str.strip().str.capitalize()
    return df

# ---------------- Load data ----------------
try:
    df = parse_google_sheet()
    if df.empty:
        st.error("Aucune donnée trouvée dans le Google Sheet. Vérifiez que les données sont bien saisies.")
        st.stop()
except Exception as e:
    st.error(f"Erreur lors de la lecture du Google Sheet : {str(e)}")
    st.stop()

df["SessionID"] = df["Mois"].astype(str) + " - " + df["Seance"].astype(str)

# ---------------- Sidebar ----------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à :", ["Classement", "Joueurs", "Gardiens"])

months_all = sorted(df["Mois"].unique())
jeux_min, jeux_max = int(df["Jeu"].min()), int(df["Jeu"].max())
joueurs_all = sorted(df[df["Postes"]!="Gardien"]["Joueur"].unique())
semaines_all = sorted(df["Semaine"].unique())
gardiens_all = sorted(df[df["Postes"]=="Gardien"]["Joueur"].unique())

# ---------------- Page Classement ----------------
if page == "Classement":
    st.header("Classements")
    
    # ========================
    # Classement des joueurs
    st.subheader("🏆 Classement des joueurs (période filtrée)")
    mois_sel_cl = st.multiselect("Mois", months_all, default=months_all, key="mois_classement_joueurs")
    semaine_sel_cl = st.multiselect("Semaine", semaines_all, default=semaines_all, key="semaine_classement_joueurs")
    jeu_range_cl = st.slider("Plage de jeux", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_classement_joueurs")
    joueurs_sel_cl = st.multiselect("Joueurs", joueurs_all, default=joueurs_all, key="joueurs_classement")

    mask_cl = (
        (df["Postes"] != "Gardien") &
        (df["Mois"].isin(mois_sel_cl)) &
        (df["Semaine"].isin(semaine_sel_cl)) &
        (df["Jeu"].between(jeu_range_cl[0], jeu_range_cl[1])) &
        (df["Joueur"].isin(joueurs_sel_cl))
    )
    df_cl = df.loc[mask_cl]

    if df_cl.empty:
        st.warning("Aucune donnée pour les filtres choisis.")
    else:
        ranking = df_cl.groupby("Joueur", as_index=False).agg({"Victoire":"sum","Défaite":"sum","Nul":"sum"})
        ranking["Total"] = ranking["Victoire"] + ranking["Défaite"]  # Les nuls ne comptent pas dans le total pour le %
        ranking["% Victoire"] = (ranking["Victoire"]/ranking["Total"]).fillna(0)
        
        # Conversion en entiers pour le formatage
        ranking["Victoire"] = ranking["Victoire"].astype(int)
        ranking["Défaite"] = ranking["Défaite"].astype(int)
        ranking["Nul"] = ranking["Nul"].astype(int)
        ranking["Total"] = ranking["Total"].astype(int)
        
        ranking = ranking.sort_values("% Victoire", ascending=False).reset_index(drop=True)
        ranking.insert(0, "Position", range(1,len(ranking)+1))
        st.dataframe(ranking.style.format({"% Victoire":"{:.2%}","Victoire":"{:d}","Défaite":"{:d}","Nul":"{:d}","Total":"{:d}"}), use_container_width=True)

    st.markdown("---")

    # ========================
    # Classement des gardiens
    if len(gardiens_all) > 0:
        st.subheader("🥅 Classement des gardiens (période filtrée)")
        mois_sel_cl_g = st.multiselect("Mois", months_all, default=months_all, key="mois_classement_gardiens")
        semaine_sel_cl_g = st.multiselect("Semaine", semaines_all, default=semaines_all, key="semaine_classement_gardiens")
        jeu_range_cl_g = st.slider("Plage de jeux", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_classement_gardiens")
        gardiens_sel_cl = st.multiselect("Gardiens", gardiens_all, default=gardiens_all, key="gardiens_classement")

        mask_cl_g = (
            (df["Postes"] == "Gardien") &
            (df["Mois"].isin(mois_sel_cl_g)) &
            (df["Semaine"].isin(semaine_sel_cl_g)) &
            (df["Jeu"].between(jeu_range_cl_g[0], jeu_range_cl_g[1])) &
            (df["Joueur"].isin(gardiens_sel_cl))
        )
        df_cl_g = df.loc[mask_cl_g]

        if df_cl_g.empty:
            st.warning("Aucune donnée gardien pour les filtres choisis.")
        else:
            # Calculer les stats par séance unique d'abord, puis les moyennes
            perf_par_seance_unique = df_cl_g.groupby(["Joueur", "Mois", "Seance", "Semaine"])["Buts_encaisses"].sum().reset_index()
            ranking_gardiens = perf_par_seance_unique.groupby("Joueur").agg({
                "Buts_encaisses": ["mean", "sum", "count"]
            }).round(2)
            ranking_gardiens.columns = ["Moyenne_buts_par_seance", "Total_buts", "Nb_seances"]
            ranking_gardiens = ranking_gardiens.reset_index()
            
            # Tri par moyenne croissante (moins de buts = meilleur)
            ranking_gardiens = ranking_gardiens.sort_values("Moyenne_buts_par_seance", ascending=True).reset_index(drop=True)
            ranking_gardiens.insert(0, "Position", range(1, len(ranking_gardiens)+1))
            
            st.dataframe(
                ranking_gardiens.style.format({
                    "Moyenne_buts_par_seance": "{:.2f}",
                    "Total_buts": "{:.0f}",
                    "Nb_seances": "{:d}"
                }),
                use_container_width=True
            )
    else:
        st.info("Aucun gardien détecté dans les données.")

# ---------------- Page Joueurs ----------------
elif page == "Joueurs":
    st.header("Graphiques et analyses — Joueurs")

    # ---------------- Graphique 1 ----------------
    st.subheader("Graphique 1 — % de victoires par jeu")
    mois_sel_g1 = st.multiselect("Mois (G1)", months_all, default=months_all)
    semaine_sel_g1 = st.multiselect("Semaine (G1)", semaines_all, default=semaines_all)
    jeu_range_g1 = st.slider("Plage de jeux (G1)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max))
    joueurs_sel_g1 = st.multiselect("Joueurs (G1)", joueurs_all, default=joueurs_all)

    mask_g1 = (
        (df["Postes"] != "Gardien") &
        (df["Mois"].isin(mois_sel_g1)) &
        (df["Semaine"].isin(semaine_sel_g1)) &
        (df["Jeu"].between(jeu_range_g1[0], jeu_range_g1[1])) &
        (df["Joueur"].isin(joueurs_sel_g1))
    )
    df_g1 = df.loc[mask_g1]
    if not df_g1.empty:
        agg1 = df_g1.groupby(["Jeu","Joueur"], as_index=False).agg({"Victoire":"sum","Défaite":"sum"})
        agg1["Total"] = agg1["Victoire"] + agg1["Défaite"]
        agg1["% Victoire"] = (agg1["Victoire"]/agg1["Total"]).fillna(0)
        agg1["Jeu_str"] = agg1["Jeu"].astype(str)
        chart1 = (
            alt.Chart(agg1)
            .mark_line(point=True)
            .encode(
                x=alt.X("Jeu_str:O", title="Numéro du jeu"),
                y=alt.Y("% Victoire:Q", title="% Victoire", axis=alt.Axis(format="%")),
                color="Joueur:N",
                tooltip=["Joueur","Jeu","% Victoire"]
            ).interactive()
        )
        st.altair_chart(chart1, use_container_width=True)

    st.markdown("---")

    # ---------------- Graphique 2 ----------------
    st.subheader("Graphique 2 — % de victoires cumulées par séance")
    mois_sel_g2 = st.multiselect("Mois (G2)", months_all, default=months_all)
    semaine_sel_g2 = st.multiselect("Semaine (G2)", semaines_all, default=semaines_all)
    jeu_range_g2 = st.slider("Plage de jeux (G2)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max))
    joueurs_sel_g2 = st.multiselect("Joueurs (G2)", joueurs_all, default=joueurs_all)

    mask_g2 = (
        (df["Postes"] != "Gardien") &
        (df["Mois"].isin(mois_sel_g2)) &
        (df["Semaine"].isin(semaine_sel_g2)) &
        (df["Jeu"].between(jeu_range_g2[0], jeu_range_g2[1])) &
        (df["Joueur"].isin(joueurs_sel_g2))
    )
    df_g2 = df.loc[mask_g2]
    if not df_g2.empty:
        # D'abord agréger par séance unique (Mois + Seance + Semaine)
        df_par_seance = df_g2.groupby(["Joueur", "Mois", "Seance", "Semaine"]).agg({
            "Victoire": "sum",
            "Défaite": "sum"
        }).reset_index()
        
        # Créer un identifiant de séance unique et trier chronologiquement
        df_par_seance["Seance_ID"] = df_par_seance["Mois"] + " - " + df_par_seance["Seance"] + " (S" + df_par_seance["Semaine"].astype(str) + ")"
        df_par_seance = df_par_seance.sort_values(["Joueur", "Mois", "Semaine"])
        
        # Calculer les pourcentages cumulés par séance
        df_par_seance["Victoire_cum"] = df_par_seance.groupby("Joueur")["Victoire"].cumsum()
        df_par_seance["Total_cum"] = df_par_seance.groupby("Joueur")[["Victoire", "Défaite"]].cumsum().sum(axis=1)
        df_par_seance["% Victoire cumulée"] = (df_par_seance["Victoire_cum"] / df_par_seance["Total_cum"]).fillna(0)
        
        chart2 = (
            alt.Chart(df_par_seance)
            .mark_line(point=True)
            .encode(
                x=alt.X("Seance_ID:O", title="Séance", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("% Victoire cumulée:Q", title="% Victoire cumulée", axis=alt.Axis(format="%")),
                color="Joueur:N",
                tooltip=["Joueur", "Seance_ID", "% Victoire cumulée", "Victoire_cum", "Total_cum"]
            ).interactive()
        )
        st.altair_chart(chart2, use_container_width=True)

    st.markdown("---")

    # ---------------- Graphique 3 ----------------
    st.subheader("Graphique 3 — Nombre total de victoires et défaites par joueur")
    mois_sel_g3 = st.multiselect("Mois (G3)", months_all, default=months_all)
    semaine_sel_g3 = st.multiselect("Semaine (G3)", semaines_all, default=semaines_all)
    jeu_range_g3 = st.slider("Plage de jeux (G3)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max))
    joueurs_sel_g3 = st.multiselect("Joueurs (G3)", joueurs_all, default=joueurs_all)

    mask_g3 = (
        (df["Postes"] != "Gardien") &
        (df["Mois"].isin(mois_sel_g3)) &
        (df["Semaine"].isin(semaine_sel_g3)) &
        (df["Jeu"].between(jeu_range_g3[0], jeu_range_g3[1])) &
        (df["Joueur"].isin(joueurs_sel_g3))
    )
    df_g3 = df.loc[mask_g3]
    if not df_g3.empty:
        agg3 = df_g3.groupby("Joueur", as_index=False).agg({"Victoire":"sum","Défaite":"sum"})
        agg3_melted = agg3.melt(id_vars="Joueur", value_vars=["Victoire","Défaite"], var_name="Type", value_name="Nombre")
        chart3 = (
            alt.Chart(agg3_melted)
            .mark_bar()
            .encode(
                x=alt.X("Joueur:N", sort=joueurs_all),
                y="Nombre:Q",
                color="Type:N",
                tooltip=["Joueur","Type","Nombre"]
            ).interactive()
        )
        st.altair_chart(chart3, use_container_width=True)

    st.markdown("---")

    # ---------------- Graphique 4 ----------------
    st.subheader("Graphique 4 — % de victoires cumulées par semaine")
    mois_sel_g4 = st.multiselect("Mois (G4)", months_all, default=months_all)
    semaine_sel_g4 = st.multiselect("Semaine (G4)", semaines_all, default=semaines_all)
    joueurs_sel_g4 = st.multiselect("Joueurs (G4)", joueurs_all, default=joueurs_all)

    mask_g4 = (
        (df["Postes"] != "Gardien") &
        (df["Mois"].isin(mois_sel_g4)) &
        (df["Semaine"].isin(semaine_sel_g4)) &
        (df["Joueur"].isin(joueurs_sel_g4))
    )
    df_g4 = df.loc[mask_g4]
    if not df_g4.empty:
        # Agréger par semaine (Mois + Semaine)
        agg4 = df_g4.groupby(["Mois", "Semaine", "Joueur"], as_index=False).agg({"Victoire":"sum","Défaite":"sum"})
        agg4 = agg4.sort_values(["Joueur", "Mois", "Semaine"])
        
        # Créer un identifiant de semaine unique pour l'affichage
        agg4["Semaine_ID"] = agg4["Mois"] + " (S" + agg4["Semaine"].astype(str) + ")"
        
        # Calculer les cumuls par joueur
        agg4["Victoire_cum"] = agg4.groupby("Joueur")["Victoire"].cumsum()
        agg4["Total_cum"] = agg4.groupby("Joueur")[["Victoire","Défaite"]].cumsum().sum(axis=1)
        agg4["% Victoire cumulée"] = (agg4["Victoire_cum"]/agg4["Total_cum"]).fillna(0)
        
        chart4 = (
            alt.Chart(agg4)
            .mark_line(point=True)
            .encode(
                x=alt.X("Semaine_ID:O", title="Semaine", axis=alt.Axis(labelAngle=-45)),
                y=alt.Y("% Victoire cumulée:Q", axis=alt.Axis(format="%")),
                color="Joueur:N",
                tooltip=["Joueur", "Semaine_ID", "% Victoire cumulée", "Victoire_cum", "Total_cum"]
            ).interactive()
        )
        st.altair_chart(chart4, use_container_width=True)

# ---------------- Page Gardiens ----------------
elif page == "Gardiens":
    st.header("Statistiques des gardiens")

    # Vérification de la présence de gardiens
    gardiens_all = sorted(df[df["Postes"] == "Gardien"]["Joueur"].unique())

    if len(gardiens_all) == 0:
        st.warning("Aucun gardien détecté dans les données. Vérifiez que la colonne 'Postes' contient bien 'Gardien'.")
        st.write("Debug - Postes uniques détectés :", df["Postes"].unique())
    else:
        # ========================
        # Graphique 1 - Buts encaissés moyens par jeu
        st.subheader("Graphique 1 — Buts encaissés moyens par jeu")
        mois_sel_g1 = st.multiselect("Mois (G1)", months_all, default=months_all, key="mois_g1")
        semaine_sel_g1 = st.multiselect("Semaine (G1)", semaines_all, default=semaines_all, key="semaine_g1")
        jeu_range_g1 = st.slider("Plage de jeux (G1)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_g1")
        gardiens_sel_g1 = st.multiselect("Gardiens (G1)", gardiens_all, default=gardiens_all, key="gardiens_g1")

        mask_g1 = (
            (df["Postes"] == "Gardien") &
            (df["Mois"].isin(mois_sel_g1)) &
            (df["Semaine"].isin(semaine_sel_g1)) &
            (df["Jeu"].between(jeu_range_g1[0], jeu_range_g1[1])) &
            (df["Joueur"].isin(gardiens_sel_g1))
        )
        df_g1 = df[mask_g1]
        
        if not df_g1.empty:
            buts_par_seance_unique = df_g1.groupby(["Mois", "Seance", "Semaine", "Jeu", "Joueur"])["Buts_encaisses"].sum().reset_index()
            buts_par_jeu = buts_par_seance_unique.groupby(["Jeu", "Joueur"])["Buts_encaisses"].mean().reset_index()
            buts_par_jeu["Jeu_str"] = buts_par_jeu["Jeu"].astype(str)
            
            chart_g1 = (
                alt.Chart(buts_par_jeu)
                .mark_bar()
                .encode(
                    x=alt.X("Jeu_str:O", title="Numéro du jeu"),
                    y=alt.Y("Buts_encaisses:Q", title="Buts encaissés (moyenne par séance)"),
                    color=alt.Color("Joueur:N", title="Gardien"),
                    tooltip=["Jeu", "Joueur", "Buts_encaisses"]
                ).interactive()
            )
            st.altair_chart(chart_g1, use_container_width=True)
        else:
            st.warning("Aucune donnée pour les filtres choisis (G1).")

        st.markdown("---")

        # ========================
        # Graphique 2 - Buts encaissés moyens par type de séance
        st.subheader("Graphique 2 — Buts encaissés moyens par type de séance")
        mois_sel_g2 = st.multiselect("Mois (G2)", months_all, default=months_all, key="mois_g2")
        semaine_sel_g2 = st.multiselect("Semaine (G2)", semaines_all, default=semaines_all, key="semaine_g2")
        jeu_range_g2 = st.slider("Plage de jeux (G2)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_g2")
        gardiens_sel_g2 = st.multiselect("Gardiens (G2)", gardiens_all, default=gardiens_all, key="gardiens_g2")

        mask_g2 = (
            (df["Postes"] == "Gardien") &
            (df["Mois"].isin(mois_sel_g2)) &
            (df["Semaine"].isin(semaine_sel_g2)) &
            (df["Jeu"].between(jeu_range_g2[0], jeu_range_g2[1])) &
            (df["Joueur"].isin(gardiens_sel_g2))
        )
        df_g2 = df[mask_g2]
        
        if not df_g2.empty:
            buts_par_seance_complete = df_g2.groupby(["Mois", "Seance", "Semaine", "Joueur"])["Buts_encaisses"].sum().reset_index()
            buts_par_type_seance = buts_par_seance_complete.groupby(["Seance", "Joueur"])["Buts_encaisses"].mean().reset_index()
            
            chart_g2 = (
                alt.Chart(buts_par_type_seance)
                .mark_bar()
                .encode(
                    x=alt.X("Seance:N", title="Type de séance"),
                    y=alt.Y("Buts_encaisses:Q", title="Buts encaissés (moyenne par séance complète)"),
                    color=alt.Color("Joueur:N", title="Gardien"),
                    tooltip=["Seance", "Joueur", "Buts_encaisses"]
                ).interactive()
            )
            st.altair_chart(chart_g2, use_container_width=True)
        else:
            st.warning("Aucune donnée pour les filtres choisis (G2).")

        st.markdown("---")

        # ========================
        # Graphique 3 - Buts encaissés totaux par mois
        st.subheader("Graphique 3 — Buts encaissés totaux par mois")
        mois_sel_g3 = st.multiselect("Mois (G3)", months_all, default=months_all, key="mois_g3")
        semaine_sel_g3 = st.multiselect("Semaine (G3)", semaines_all, default=semaines_all, key="semaine_g3")
        jeu_range_g3 = st.slider("Plage de jeux (G3)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_g3")
        gardiens_sel_g3 = st.multiselect("Gardiens (G3)", gardiens_all, default=gardiens_all, key="gardiens_g3")

        mask_g3 = (
            (df["Postes"] == "Gardien") &
            (df["Mois"].isin(mois_sel_g3)) &
            (df["Semaine"].isin(semaine_sel_g3)) &
            (df["Jeu"].between(jeu_range_g3[0], jeu_range_g3[1])) &
            (df["Joueur"].isin(gardiens_sel_g3))
        )
        df_g3 = df[mask_g3]
        
        if not df_g3.empty:
            buts_par_mois_complet = df_g3.groupby(["Mois", "Joueur"])["Buts_encaisses"].sum().reset_index()
            
            chart_g3 = (
                alt.Chart(buts_par_mois_complet)
                .mark_bar()
                .encode(
                    x=alt.X("Mois:N", title="Mois"),
                    y=alt.Y("Buts_encaisses:Q", title="Total buts encaissés dans le mois"),
                    color=alt.Color("Joueur:N", title="Gardien"),
                    tooltip=["Mois", "Joueur", "Buts_encaisses"]
                ).interactive()
            )
            st.altair_chart(chart_g3, use_container_width=True)
        else:
            st.warning("Aucune donnée pour les filtres choisis (G3).")

        st.markdown("---")

        # ========================
        # Graphique 4 - Performance individuelle des gardiens
        st.subheader("Graphique 4 — Performance individuelle des gardiens")
        mois_sel_g4 = st.multiselect("Mois (G4)", months_all, default=months_all, key="mois_g4")
        semaine_sel_g4 = st.multiselect("Semaine (G4)", semaines_all, default=semaines_all, key="semaine_g4")
        jeu_range_g4 = st.slider("Plage de jeux (G4)", min_value=jeux_min, max_value=jeux_max, value=(jeux_min, jeux_max), key="jeu_g4")
        gardiens_sel_g4 = st.multiselect("Gardiens (G4)", gardiens_all, default=gardiens_all, key="gardiens_g4")

        mask_g4 = (
            (df["Postes"] == "Gardien") &
            (df["Mois"].isin(mois_sel_g4)) &
            (df["Semaine"].isin(semaine_sel_g4)) &
            (df["Jeu"].between(jeu_range_g4[0], jeu_range_g4[1])) &
            (df["Joueur"].isin(gardiens_sel_g4))
        )
        df_g4 = df[mask_g4]
        
        if not df_g4.empty:
            perf_par_seance_unique = df_g4.groupby(["Joueur", "Mois", "Seance", "Semaine"])["Buts_encaisses"].sum().reset_index()
            perf_gardiens = perf_par_seance_unique.groupby("Joueur").agg({
                "Buts_encaisses": ["mean", "sum", "count"]
            }).round(2)
            perf_gardiens.columns = ["Moyenne_buts_par_seance", "Total_buts", "Nb_seances"]
            perf_gardiens = perf_gardiens.reset_index()
            
            chart_g4 = (
                alt.Chart(perf_gardiens)
                .mark_bar()
                .encode(
                    x=alt.X("Joueur:N", title="Gardien"),
                    y=alt.Y("Moyenne_buts_par_seance:Q", title="Moyenne de buts encaissés par séance"),
                    tooltip=["Joueur", "Moyenne_buts_par_seance", "Total_buts", "Nb_seances"]
                ).interactive()
            )
            st.altair_chart(chart_g4, use_container_width=True)

            # ========================
            # Tableau de synthèse gardiens
            st.subheader("📊 Synthèse des performances des gardiens")
            st.dataframe(
                perf_gardiens.style.format({
                    "Moyenne_buts_par_seance": "{:.2f}",
                    "Total_buts": "{:.0f}",
                    "Nb_seances": "{:d}"
                }),
                use_container_width=True
            )
        else:
            st.warning("Aucune donnée pour les filtres choisis (G4).")


st.markdown("---")
st.caption("Astuce : le slider 'Plage de jeux' filtre les numéros de jeu. Les semaines sont calculées à partir du jour de la semaine.")
