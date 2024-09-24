from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from model import predict
import json
import os
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Autoriser toutes les origines. Pour des raisons de sécurité, vous devriez spécifier des origines précises.
    allow_credentials=True,
    allow_methods=["*"],  # Autoriser toutes les méthodes HTTP. Vous pouvez spécifier les méthodes spécifiques comme ["GET", "POST"]
    allow_headers=["*"],  # Autoriser tous les en-têtes. Vous pouvez spécifier les en-têtes spécifiques comme ["Content-Type"]
)


# Définir un modèle Pydantic pour valider les entrées
class PredictRequest(BaseModel):
    client_id: str
    montant_demande: float
    taux_interet: float
    periode_remboursement: int

# Nom du fichier d'historique
HISTORIQUE_FILE = "historique.json"

def ajouter_historique(data: dict):
    # Créer le fichier s'il n'existe pas
    if not os.path.exists(HISTORIQUE_FILE):
        with open(HISTORIQUE_FILE, 'w') as f:
            json.dump([], f)
    
    # Lire le contenu actuel
    with open(HISTORIQUE_FILE, 'r') as f:
        historique = json.load(f)
    
    # Ajouter la nouvelle entrée
    historique.append(data)
    
    # Écrire les données mises à jour dans le fichier
    with open(HISTORIQUE_FILE, 'w') as f:
        json.dump(historique, f)

@app.post("/verifier")
async def verifier(params: PredictRequest):
    try:
        # Appeler la fonction predict avec les paramètres
        result = predict(params.client_id, params.montant_demande, params.taux_interet, params.periode_remboursement)
        
        # Préparer les données pour l'historique
        historique_entry = {
            "timestamp": datetime.now().isoformat(),
            "client_id": params.client_id,
            "montant_demande": params.montant_demande,
            "taux_interet": params.taux_interet,
            "periode_remboursement": params.periode_remboursement,
            "result": result
        }
        
        # Ajouter les données à l'historique
        ajouter_historique(historique_entry)
        
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.options("/verifier")
async def options_verifier():
    return JSONResponse(
        content={},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.get("/historique")
async def obtenir_historique():
    if not os.path.exists(HISTORIQUE_FILE):
        raise HTTPException(status_code=404, detail="Aucun historique trouvé")
    
    with open(HISTORIQUE_FILE, 'r') as f:
        historique = json.load(f)
    
    return {"historique": historique[-4:]}


@app.get("/")
async def index():
    return {"ECO PREDICT"}