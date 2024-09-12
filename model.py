import polars as pl
import numpy as np

# Préparer les données pour le calcul de solvabilité
def preparer_donnees(df):
    df = df.with_columns([
        # Calcul des transactions mensuelles nettes
        (pl.col('credit_Janvier_2023') + pl.col('credit_Fevrier_2023') +
         pl.col('credit_Mars_2023') + pl.col('credit_Avril_2023') -
         pl.col('debit_Janvier_2023') - pl.col('debit_Fevrier_2023') -
         pl.col('debit_Mars_2023') - pl.col('debit_Avril_2023')).alias('transactions_mensuelles'),
        
        # Estimation du revenu mensuel comme la moyenne des crédits mensuels
        ((pl.col('credit_Janvier_2023') + pl.col('credit_Fevrier_2023') +
          pl.col('credit_Mars_2023') + pl.col('credit_Avril_2023')) / 4).alias('revenu_mensuel')
    ])
    return df

# Calcul des paramètres financiers et de la solvabilité
def calculer_solvabilite(df, montant_demande, taux_interet, periode_remboursement):
    taux_interet_expr = pl.lit(taux_interet)
    periode_remboursement_expr = pl.lit(periode_remboursement)
    montant_demande_expr = pl.lit(montant_demande)
    
    # Calcul du plafond de prêt (40% du revenu mensuel)
    df = df.with_columns([
        (pl.col('revenu_mensuel') * 0.4).alias('plafond_pret')  # Mensualité maximale
    ])
    
    # Calcul de la mensualité
    df = df.with_columns([
        pl.when(taux_interet_expr != 0).then(
            montant_demande_expr * ((taux_interet_expr / 12) / 
            (1 - (1 + (taux_interet_expr / 12)) ** -periode_remboursement_expr))
        ).otherwise(0).alias('mensualite')  # Mensualité calculée
    ])
    
    # Calcul du prêt maximum supportable
    df = df.with_columns([
        pl.when(pl.col('plafond_pret') > 0).then(
            (pl.col('plafond_pret') * (1 - (1 + (taux_interet_expr / 12)) ** -periode_remboursement_expr)) / (taux_interet_expr / 12)
        ).otherwise(0).alias('pret_max')  # Prêt maximum supportable
    ])
    
    # Calcul du pourcentage de solvabilité  
    df = df.with_columns([
        pl.when(pl.col('pret_max') > 0).then(
            (montant_demande_expr / pl.col('pret_max')) * 100
        ).otherwise(0).alias('pourcentage_solvabilite')  # Utiliser 0 pour éviter NaN
    ])
    
    # Calcul de la probabilité de remboursement
    df = df.with_columns([
        pl.when(pl.col('revenu_mensuel') > 0).then(
            (1 - pl.col('mensualite') / pl.col('revenu_mensuel')) * 100
        ).otherwise(np.nan).alias('probabilite_remboursement')
    ])
    
    # Classification de la solvabilité
    df = df.with_columns([
        pl.when(pl.col('pourcentage_solvabilite') <= 60)
        .then(pl.lit('Solvabilité élevée'))
        .when((pl.col('pourcentage_solvabilite') > 60) & (pl.col('pourcentage_solvabilite') <= 80))
        .then(pl.lit('Solvabilité moyenne'))
        .when((pl.col('pourcentage_solvabilite') > 80) & (pl.col('pourcentage_solvabilite') <= 100))
        .then(pl.lit('Solvabilité faible'))
        .otherwise(pl.lit('Non solvable')).alias('classification_solvabilite')
    ])
    
    return df

def calculer_pret_optimal(df):
    # Calculer le montant du prêt optimal basé sur le plafond de prêt et la capacité de remboursement
    df = df.with_columns([
        pl.col('pret_max').alias('pret_optimal')
    ])
    
    # S'assurer que le prêt optimal ne soit pas négatif
    df = df.with_columns([
        pl.when(pl.col('pret_optimal') > 0).then(pl.col('pret_optimal')).otherwise(0).alias('pret_optimal')
    ])
    
    return df

def verifier_solvabilite(df, client_id, montant_demande, taux_interet, periode_remboursement):
    # Filtrer les données pour le client spécifié avant les calculs
    df_client = df.filter(pl.col('ac_no') == client_id)
    
    if df_client.shape[0] == 0:
        return {"message": f"Aucun résultat trouvé pour le client {client_id}"}

    # Préparation des données
    df_client_prep = preparer_donnees(df_client)
    
    # Calcul de la solvabilité
    df_client_resultat = calculer_solvabilite(df_client_prep, montant_demande, taux_interet, periode_remboursement)
    
    # Calcul du prêt optimal si nécessaire
    df_client_resultat = calculer_pret_optimal(df_client_resultat)
    
    # Conversion des résultats en format JSON
    resultats = []
    for row in df_client_resultat.iter_rows(named=True):
        if round(row['probabilite_remboursement'], 2) < 0:
            row['probabilite_remboursement'] = 0
        elif round(row['probabilite_remboursement'], 2) > 100:
            row['probabilite_remboursement'] = 100
            
        resultats.append({
        "client_id": row['ac_no'],
        "montant_demandé": round(montant_demande, 2),
        "revenu_mensuel estimé": round(row['revenu_mensuel'], 2),
        "mensualité_maximale_admissible": round(row['plafond_pret'], 2),
        "proportion_prêt_vs_prêt_max_allouable": round(row['pourcentage_solvabilite'], 2),
        "classification_solvabilité": row['classification_solvabilite'],
        "pret_max_allouable": round(row['pret_max'], 2),
        "mensualite_calculée": round(row['mensualite'], 2),
        "probabilite_remboursement": round(row['probabilite_remboursement'], 2),
        "prêt_optimal": round(row.get('pret_optimal', 0.0), 2)
    })
    return resultats

def predict(client_id="N23017007413", montant_demande=150000000, taux_interet=0.05, periode_remboursement=60):
    df = pl.read_parquet("data/base_t2_.parquet")
    return verifier_solvabilite(df, client_id, montant_demande, taux_interet, periode_remboursement)
