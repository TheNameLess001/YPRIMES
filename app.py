import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Prime Manager Pro",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONNALISÉ (Pour garder ton style) ---
st.markdown("""
    <style>
    /* Style général */
    .main { background-color: #f8fafc; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; color: #1e293b; }
    
    /* Cartes de métriques */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e2e8f0;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 4px;
        color: #64748b;
        font-weight: 600;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff;
        color: #2563eb;
        border-bottom: 2px solid #2563eb;
    }
    
    /* Boutons */
    .stButton button {
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- GESTION BASE DE DONNÉES (SQLite) ---
def init_db():
    conn = sqlite3.connect('primes_data.db')
    c = conn.cursor()
    # Table Sales
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
                 id TEXT PRIMARY KEY, month TEXT, year INTEGER, 
                 collab_name TEXT, acquisition_real INTEGER, 
                 total_stores INTEGER, active_stores INTEGER)''')
    # Table AM
    c.execute('''CREATE TABLE IF NOT EXISTS am (
                 id TEXT PRIMARY KEY, month TEXT, year INTEGER,
                 collab_name TEXT, gmv_prev REAL, gmv_curr REAL,
                 total_stores INTEGER, automated_stores INTEGER, quality_deals INTEGER)''')
    conn.commit()
    conn.close()

def load_data(table, month, year):
    conn = sqlite3.connect('primes_data.db')
    query = f"SELECT * FROM {table} WHERE month = ? AND year = ?"
    df = pd.read_sql(query, conn, params=(month, year))
    conn.close()
    return df

def save_data(table, df, month, year):
    conn = sqlite3.connect('primes_data.db')
    # On supprime les anciennes données du mois pour éviter les doublons (méthode simple)
    c = conn.cursor()
    c.execute(f"DELETE FROM {table} WHERE month = ? AND year = ?", (month, year))
    conn.commit()
    
    # On ajoute les métadonnées de temps
    df['month'] = month
    df['year'] = year
    # On génère un ID unique si pas présent
    if 'id' not in df.columns:
        df['id'] = df.apply(lambda x: f"{year}_{month}_{x.name}", axis=1)
        
    df.to_sql(table, conn, if_exists='append', index=False)
    conn.close()

# --- INITIALISATION ---
init_db()

# --- BARRE LATÉRALE (Navigation & Filtres) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=50)
    st.title("Prime Manager")
    
    st.markdown("---")
    
    # Navigation
    page = st.radio("Navigation", ["📝 Saisie & Calcul", "📊 Dashboard & Flop/Top", "📁 Export & Admin"])
    
    st.markdown("---")
    
    # Sélecteur de date global
    st.subheader("📅 Période")
    col1, col2 = st.columns(2)
    current_year = datetime.now().year
    current_month_idx = datetime.now().month - 1
    
    months_list = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
    
    selected_year = col1.selectbox("Année", [2024, 2025, 2026, 2027], index=1)
    selected_month = col2.selectbox("Mois", months_list, index=current_month_idx)

    # Configuration Jours Fériés (Simplifiée)
    st.subheader("⚙️ Paramètres")
    holidays_count = st.number_input("Jours Fériés ce mois", min_value=0, max_value=10, value=0)
    
    # Calcul Jours Ouvrés (Approximation simple Lundi-Vendredi)
    # Pour une vraie prod, utiliser la librairie 'holidays' ou numpy.busday_count
    def get_business_days(year, month_name, holidays):
        month_num = months_list.index(month_name) + 1
        start_date = date(year, month_num, 1)
        if month_num == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month_num + 1, 1)
        
        bus_days = np.busday_count(start_date, end_date)
        return max(0, bus_days - holidays)

    business_days = get_business_days(selected_year, selected_month, holidays_count)
    st.info(f"📆 Jours ouvrés : **{business_days}**")
    
    # Targets Dynamiques
    sales_target_acq = round(business_days * 0.9, 1)

# --- PAGE 1: SAISIE & CALCUL ---
if page == "📝 Saisie & Calcul":
    st.title(f"Gestion des Primes - {selected_month} {selected_year}")
    
    tab_sales, tab_am = st.tabs(["🛍️ Équipe SALES", "📈 Équipe AM"])
    
    # --- LOGIQUE SALES ---
    with tab_sales:
        st.markdown(f"**Objectifs :** Acquisition > **{sales_target_acq}** | Perf Stores > **70%**")
        
        # Chargement données
        df_sales = load_data('sales', selected_month, selected_year)
        
        if df_sales.empty:
            # Création structure vide si pas de données
            data = {
                'collab_name': [f'Collab {i}' for i in range(1, 11)],
                'acquisition_real': [0]*10,
                'total_stores': [10]*10,
                'active_stores': [0]*10
            }
            df_sales = pd.DataFrame(data)

        # Editeur de données
        edited_sales = st.data_editor(
            df_sales,
            column_config={
                "collab_name": "Collaborateur",
                "acquisition_real": st.column_config.NumberColumn("Acquisition", help=f"Obj: {sales_target_acq}", min_value=0),
                "total_stores": st.column_config.NumberColumn("Total Portefeuille", min_value=1),
                "active_stores": st.column_config.NumberColumn("Stores Actifs (>5 cmds)", min_value=0),
                "id": None, "month": None, "year": None # Cacher ces colonnes
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Calculs en temps réel pour affichage
        edited_sales['% Perf'] = (edited_sales['active_stores'] / edited_sales['total_stores']).fillna(0)
        edited_sales['Eligible'] = (edited_sales['acquisition_real'] >= sales_target_acq) & (edited_sales['% Perf'] >= 0.7)
        
        # KPIs globaux
        col1, col2, col3 = st.columns(3)
        col1.metric("Acquisition Totale", edited_sales['acquisition_real'].sum())
        col2.metric("Primes Validées", f"{edited_sales['Eligible'].sum()} / {len(edited_sales)}")
        col3.metric("Taux Activité Global", f"{edited_sales['% Perf'].mean():.1%}")

        if st.button("💾 Sauvegarder SALES", type="primary"):
            save_data('sales', edited_sales[['collab_name', 'acquisition_real', 'total_stores', 'active_stores']], selected_month, selected_year)
            st.success("Données Sales sauvegardées !")

    # --- LOGIQUE AM ---
    with tab_am:
        st.markdown(f"**Objectifs :** Growth > **30%** | Auto > **80%** | Deals > **3**")
        
        df_am = load_data('am', selected_month, selected_year)
        
        if df_am.empty:
            data_am = {
                'collab_name': [f'Collab {i}' for i in range(1, 11)],
                'gmv_prev': [10000.0]*10,
                'gmv_curr': [10000.0]*10,
                'total_stores': [20]*10,
                'automated_stores': [0]*10,
                'quality_deals': [0]*10
            }
            df_am = pd.DataFrame(data_am)

        edited_am = st.data_editor(
            df_am,
            column_config={
                "collab_name": "Collaborateur",
                "gmv_prev": st.column_config.NumberColumn("GMV M-1", format="%.2f €"),
                "gmv_curr": st.column_config.NumberColumn("GMV M", format="%.2f €"),
                "total_stores": "Portefeuille",
                "automated_stores": "Stores Auto",
                "quality_deals": st.column_config.NumberColumn("Deals Quali", help="Obj: 3"),
                "id": None, "month": None, "year": None
            },
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        # Calculs
        edited_am['Growth'] = ((edited_am['gmv_curr'] - edited_am['gmv_prev']) / edited_am['gmv_prev']).fillna(0)
        edited_am['% Auto'] = (edited_am['automated_stores'] / edited_am['total_stores']).fillna(0)
        edited_am['Eligible'] = (edited_am['Growth'] >= 0.30) & (edited_am['% Auto'] >= 0.80) & (edited_am['quality_deals'] >= 3)

        # Affichage visuel des résultats (Tableau stylisé)
        st.subheader("Prévisualisation Résultats")
        st.dataframe(
            edited_am[['collab_name', 'Growth', '% Auto', 'Eligible']].style.format({
                'Growth': '{:.1%}', 
                '% Auto': '{:.1%}'
            }).applymap(lambda x: 'background-color: #dcfce7; color: #166534' if x else 'background-color: #fee2e2; color: #991b1b', subset=['Eligible']),
            use_container_width=True
        )

        if st.button("💾 Sauvegarder AM", type="primary"):
            save_data('am', edited_am[['collab_name', 'gmv_prev', 'gmv_curr', 'total_stores', 'automated_stores', 'quality_deals']], selected_month, selected_year)
            st.success("Données AM sauvegardées !")

# --- PAGE 2: DASHBOARD & ANALYTICS ---
elif page == "📊 Dashboard & Flop/Top":
    st.title("Tableau de Bord de Performance")
    
    # Récupérer TOUTES les données de l'année
    conn = sqlite3.connect('primes_data.db')
    df_all_sales = pd.read_sql(f"SELECT * FROM sales WHERE year = {selected_year}", conn)
    df_all_am = pd.read_sql(f"SELECT * FROM am WHERE year = {selected_year}", conn)
    conn.close()
    
    if df_all_sales.empty:
        st.warning("Pas assez de données pour générer des analyses. Veuillez sauvegarder des données dans l'onglet Saisie.")
    else:
        # Calculs Analytics
        df_all_sales['% Perf'] = df_all_sales['active_stores'] / df_all_sales['total_stores']
        
        # 1. PODIUM
        st.subheader("🏆 Le Podium du Mois")
        col1, col2 = st.columns(2)
        
        # Top Sales (Basé sur acquisition)
        curr_sales = df_all_sales[df_all_sales['month'] == selected_month].sort_values(by='acquisition_real', ascending=False).head(3)
        if not curr_sales.empty:
            fig_podium = px.bar(curr_sales, x='collab_name', y='acquisition_real', title="Top 3 Sales (Acquisition)", 
                                color='acquisition_real', color_continuous_scale='Blues')
            col1.plotly_chart(fig_podium, use_container_width=True)
            
        # Top AM (Basé sur Growth)
        # Note: Growth recalculé car non stocké en dur
        df_all_am['Growth'] = (df_all_am['gmv_curr'] - df_all_am['gmv_prev']) / df_all_am['gmv_prev']
        curr_am = df_all_am[df_all_am['month'] == selected_month].sort_values(by='Growth', ascending=False).head(3)
        if not curr_am.empty:
            fig_podium_am = px.bar(curr_am, x='collab_name', y='Growth', title="Top 3 AM (Croissance)",
                                   color='Growth', color_continuous_scale='Greens')
            col2.plotly_chart(fig_podium_am, use_container_width=True)

        st.markdown("---")
        
        # 2. FLOP & TOP ANALYSE
        st.subheader("📉 Analyse Top & Flop (Trimestriel)")
        quarter_map = {'Q1': ['Janvier', 'Février', 'Mars'], 'Q2': ['Avril', 'Mai', 'Juin'], 
                       'Q3': ['Juillet', 'Août', 'Septembre'], 'Q4': ['Octobre', 'Novembre', 'Décembre']}
        selected_quarter = st.selectbox("Choisir le trimestre", list(quarter_map.keys()))
        
        quarter_months = quarter_map[selected_quarter]
        
        # Filtre Sales Trimestre
        df_q_sales = df_all_sales[df_all_sales['month'].isin(quarter_months)]
        
        if not df_q_sales.empty:
            # Agrégation par collaborateur
            sales_agg = df_q_sales.groupby('collab_name')[['acquisition_real', 'total_stores', 'active_stores']].sum().reset_index()
            sales_agg['Avg Perf'] = sales_agg['active_stores'] / sales_agg['total_stores']
            
            col1, col2 = st.columns(2)
            
            # Scatter Plot: Acquisition vs Qualité
            fig_scatter = px.scatter(sales_agg, x='acquisition_real', y='Avg Perf', text='collab_name', size='total_stores',
                                     title="Matrice Performance Sales (Volume vs Qualité)",
                                     labels={'acquisition_real': 'Volume Acquisition', 'Avg Perf': 'Qualité (% Stores Actifs)'},
                                     color='Avg Perf', color_continuous_scale='RdYlGn')
            # Ajout lignes médianes
            fig_scatter.add_hline(y=0.7, line_dash="dash", line_color="red", annotation_text="Objectif Qualité")
            col1.plotly_chart(fig_scatter, use_container_width=True)
            
            # Flop 5 (Ceux qui sont loin de l'objectif)
            flop_sales = sales_agg.sort_values(by='Avg Perf').head(5)
            fig_flop = px.bar(flop_sales, x='Avg Perf', y='collab_name', orientation='h', title="Alertes Performance (Bas de classement)",
                              color='Avg Perf', color_continuous_scale='Reds_r')
            col2.plotly_chart(fig_flop, use_container_width=True)

# --- PAGE 3: EXPORT & ADMIN ---
elif page == "📁 Export & Admin":
    st.title("Administration")
    
    password = st.text_input("Mot de passe Admin", type="password")
    
    if password == "admin123": # Mettre un vrai système de hachage pour la prod
        st.success("Accès autorisé")
        
        st.subheader("Exports Globaux")
        
        conn = sqlite3.connect('primes_data.db')
        
        col1, col2 = st.columns(2)
        with col1:
            df_export_sales = pd.read_sql("SELECT * FROM sales", conn)
            st.download_button(
                label="📥 Télécharger Historique Sales (CSV)",
                data=df_export_sales.to_csv(index=False).encode('utf-8'),
                file_name='historique_sales.csv',
                mime='text/csv',
            )
            
        with col2:
            df_export_am = pd.read_sql("SELECT * FROM am", conn)
            st.download_button(
                label="📥 Télécharger Historique AM (CSV)",
                data=df_export_am.to_csv(index=False).encode('utf-8'),
                file_name='historique_am.csv',
                mime='text/csv',
            )
        conn.close()
        
        st.markdown("---")
        st.subheader("Zone Danger")
        if st.button("⚠️ Réinitialiser toute la base de données"):
            conn = sqlite3.connect('primes_data.db')
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS sales")
            c.execute("DROP TABLE IF EXISTS am")
            conn.commit()
            conn.close()
            init_db() # Recreate empty tables
            st.error("Base de données réinitialisée !")
            
    elif password:
        st.error("Mot de passe incorrect")
