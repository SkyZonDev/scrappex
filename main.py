from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import logging
from typing import List
from uuid import uuid4
from dotenv import dotenv_values
config = dotenv_values(".env")

# Importez vos fonctions existantes
from function import perform_timed_purchase_batch

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constantes
BASE_URL = config["BASE_URL"]
LOGIN = config["LOGIN"]
PASSWORD = config["PASSWORD"]

# Dictionnaire pour stocker les résultats des achats
purchase_results = {}

class PurchaseRequest(BaseModel):
    lots: List[int]
    purchase_times: List[datetime]

app = FastAPI()

@app.post("/schedule-purchases")
async def schedule_purchases(request: PurchaseRequest, background_tasks: BackgroundTasks):
    """
    Endpoint pour planifier des achats avec suivi de résultats
    """
    # Générer un identifiant unique pour cette requête
    request_id = str(uuid4())

    try:
        # Initialiser les résultats avec un statut en attente
        purchase_results[request_id] = {
            "status": "pending",
            "lots": request.lots,
            "purchase_times": request.purchase_times,
            "results": None,
            "error": None
        }

        # Ajoute la tâche à l'arrière-plan
        background_tasks.add_task(
            perform_purchases,
            request_id,
            request.lots,
            request.purchase_times
        )

        return {
            "status": "success",
            "request_id": request_id,
            "message": f"{len(request.lots)} lots schedulés pour achat"
        }
    except Exception as e:
        # En cas d'erreur, mettre à jour les résultats
        purchase_results[request_id]["status"] = "error"
        purchase_results[request_id]["error"] = str(e)

        logger.error(f"Erreur de planification : {e}")
        return {"status": "error", "message": str(e)}

@app.get("/purchase-status/{request_id}")
async def get_purchase_status(request_id: str):
    """
    Endpoint pour récupérer le statut des achats
    """
    result = purchase_results.get(request_id)

    if not result:
        return {"status": "not_found", "message": "ID de requête invalide"}

    return result

async def perform_purchases(request_id: str, lots: List[int], purchase_times: List[datetime]):
    """
    Fonction pour exécuter réellement les achats et mettre à jour les résultats
    """
    try:
        results = await perform_timed_purchase_batch(
            BASE_URL,
            LOGIN,
            PASSWORD,
            lots,
            purchase_times
        )

        # Mettre à jour les résultats
        purchase_results[request_id].update({
            "status": "completed",
            "results": results
        })

        # Loggez les résultats
        for result in results:
            logger.info(f"Achat lot {result['lot']}: {'Succès' if result['success'] else 'Échec'}")

    except Exception as e:
        # En cas d'erreur, mettre à jour les résultats
        purchase_results[request_id].update({
            "status": "error",
            "error": str(e)
        })
        logger.error(f"Erreur lors des achats : {e}")

# Lancez avec uvicorn
# uvicorn main:app --reload
