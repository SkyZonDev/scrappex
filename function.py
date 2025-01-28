import aiohttp
import asyncio
import time
import logging
import json
import random
from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urljoin
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('purchase_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LoginError(Exception):
    pass

@asynccontextmanager
async def get_optimized_session(timeout: float):
    """Session optimisée avec gestion améliorée des connexions"""
    timeout_obj = aiohttp.ClientTimeout(
        total=timeout,     
        connect=10.0,      # Augmentation du timeout de connexion
        sock_connect=10.0, 
        sock_read=15.0     # Lecture plus longue
    )
    
    conn = aiohttp.TCPConnector(
        limit=50,              # Augmentation de la limite de connexions
        limit_per_host=15,     # Limite par hôte augmentée
        ttl_dns_cache=3600,    
        use_dns_cache=True,
        force_close=False,
        keepalive_timeout=90,  # Keepalive plus long
        ssl=False,             
        enable_cleanup_closed=True
    )

    try:
        session = aiohttp.ClientSession(
            connector=conn,
            timeout=timeout_obj,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/html,application/xhtml+xml",
                "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
                'X-Requested-With': 'XMLHttpRequest',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache'
            },
            cookie_jar=aiohttp.CookieJar(unsafe=True)
        )

        try:
            yield session
        finally:
            pass

    except Exception as e:
        logger.error(f"Erreur de création de session : {e}")
        raise

async def fetch_login_page(session: aiohttp.ClientSession, login_url: str) -> Tuple[str, str]:
    """Fetch login page and extract CSRF token and login token"""
    async with session.get(login_url) as response:
        text = await response.text()
        csrf_cookie = response.cookies.get('ceo_csrf_cookie')
        if not csrf_cookie:
            raise LoginError("CSRF cookie missing")

        # Optimized BeautifulSoup parsing with lxml and SoupStrainer
        soup = BeautifulSoup(text, 'lxml', parse_only=SoupStrainer('input', {'name': 'loginToken'}))
        login_token = soup.find('input', {'name': 'loginToken'})
        if not login_token or 'value' not in login_token.attrs:
            raise LoginError("Login token not found")

        return csrf_cookie.value, login_token['value']

async def login_to_website(
    base_url: str,
    login_string: str,
    login_pass: str,
    timeout: float = 2.0,
) -> Tuple[bool, float, Dict[str, float], Optional[aiohttp.ClientSession], Optional[str]]:
    """Optimized login function with better error handling and performance"""
    start_time = time.monotonic()
    metrics = defaultdict(float)

    async with get_optimized_session(timeout) as session:
        try:
            login_url = urljoin(base_url, 'login')

            # Fetch login page and tokens
            login_start = time.monotonic()
            csrf_token, login_token = await fetch_login_page(session, login_url)
            metrics['login_preparation'] = time.monotonic() - login_start

            # Perform authentication
            auth_start = time.monotonic()
            login_data = {
                'ceo_csrf_token': csrf_token,
                'loginToken': login_token,
                'login_string': login_string,
                'login_pass': login_pass
            }

            async with session.post(login_url, data=login_data) as auth_response:
                auth_text = await auth_response.text()
                if "error" in auth_text.lower() or 'login' in str(auth_response.url):
                    raise LoginError("Login failed")
                metrics['authentication'] = time.monotonic() - auth_start

            total_time = time.monotonic() - start_time
            metrics['total'] = total_time

            return True, total_time, dict(metrics), session, csrf_token

        except Exception as e:
            logger.error(f"Error during login process: {str(e)}")
            total_time = time.monotonic() - start_time
            return False, total_time, {'error': str(e), 'total': total_time}, None, None

async def perform_concurrent_purchases(
    session: aiohttp.ClientSession,
    base_url: str,
    csrf_token: str,
    lot: int,
    buyer_code: str,
    attempts: int = 5
) -> Optional[Dict]:
    """Tentatives d'achat concurrentes avec gestion d'erreurs détaillée"""
    purchase_url = urljoin(base_url, 'achat/action')
    purchase_data = {
            'ceo_csrf_token': csrf_token,
            'lot': str(lot),
            'code': buyer_code
        }

    # Préparer toutes les requêtes à l'avance
    async def single_purchase_attempt():
        start_time = time.perf_counter()
        logger.info(f"Tentative d'achat pour le Lot {lot} à {datetime.now().strftime('%H:%M:%S.%f')}")
        try:
            async with session.post(purchase_url, data=purchase_data, timeout=aiohttp.ClientTimeout(total=10), headers={'Cache-Control': 'no-cache, no-store'}) as response:
                response_text = await response.text()
                request_time = (time.perf_counter() - start_time) * 1000  # ms

                logger.debug(f"Temps de la requête pour le Lot {lot}: {request_time:.2f}ms")
                logger.debug(f"Statut de la réponse pour Lot {lot}: {response.status}")
                logger.debug(f"Texte de la réponse: {response_text[:500]}...")  # Tronqué pour éviter les logs énormes

                try:
                    parsed_response = json.loads(response_text)
                    success = response.status == 200 and parsed_response.get('statut') == 'success'
                    
                    return {
                        'request': True,
                        'success': success,
                        'status_code': response.status,
                        'response_text': response_text,
                        'duration_ms': request_time,
                        'parsed_response': parsed_response,
                        'timestamp': datetime.now()
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Impossible de décoder la réponse JSON pour Lot {lot}")
                    return {
                        'request': False,
                        'success': False,
                        'status_code': response.status,
                        'response_text': response_text,
                        'duration_ms': request_time,
                        'error': 'JSON decode error',
                        'timestamp': datetime.now()
                    }

        except aiohttp.ClientConnectionError as conn_err:
            logger.error(f"Erreur de connexion pour Lot {lot}: {conn_err}")
        except aiohttp.ClientResponseError as resp_err:
            logger.error(f"Erreur de réponse pour Lot {lot}: {resp_err}")
        except asyncio.TimeoutError:
            logger.error(f"Délai dépassé pour Lot {lot}")
        except Exception as e:
            logger.error(f"Erreur inattendue pour Lot {lot}: {type(e).__name__} - {e}")

        return {
            'success': False,
            'error': str(e) if 'e' in locals() else 'Unknown error',
            'duration_ms': (time.perf_counter() - start_time) * 1000,
            'timestamp': datetime.now()
        }

    # Créer des tâches concurrentes
    tasks = [single_purchase_attempt() for _ in range(attempts)]
    results = await asyncio.gather(*tasks)
    
    # Trier les résultats par timestamp pour avoir le plus rapide
    valid_results = [r for r in results if not r.get('error', None)]
    if valid_results:
        sorted_results = sorted(valid_results, key=lambda x: x['timestamp'])
        return sorted_results[0]

    return None

async def perform_synchronized_purchase(
    session: aiohttp.ClientSession,
    base_url: str,
    csrf_token: str,
    lot: int,
    password: str,
    purchase_time: datetime
) -> dict:
    """Synchronise l'achat avec pré-initialisation des connexions"""
    purchase_url = urljoin(base_url, 'achat/action')

    # Calcul précis du temps d'attente
    time_to_wait = (purchase_time - datetime.now()).total_seconds()
    logger.info(f"Préparation achat Lot {lot}")
    logger.info(f"Temps d'attente: {time_to_wait} secondes")
    
    # Pré-initialisation des connexions TCP
    async def warmup_connection():
        async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=2)) as response:
            await response.text()
    
    # Préparer les connexions 5 secondes avant l'achat
    while (purchase_time - datetime.now()).total_seconds() > 3:
        await asyncio.sleep(0.001)  # Attente plus courte pour plus de précision
        
    logger.debug(f"Pré-initialisation des connexions pour Lot {lot}")
    await warmup_connection()
    
    # Préparation des données de la requête
    purchase_data = {
        'ceo_csrf_token': csrf_token,
        'lot': str(lot),
        'code': password
    }
    
    # Synchronisation fine
    while datetime.now() < purchase_time:
        await asyncio.sleep(0.001)  # Attente plus courte pour plus de précision
    
    sync_offset = (datetime.now() - purchase_time).total_seconds()
    logger.info(f"Décalage réel de synchronisation: {sync_offset * 1000:.2f} ms")
    
    # Création des coroutines de requête à l'avance
    start_time = time.perf_counter()
    async def make_request():
        try:
            logger.info(f"Tentative d'achat pour le Lot {lot} à {datetime.now().strftime('%H:%M:%S.%f')}")
            async with session.post(
                purchase_url,
                data=purchase_data,
                timeout=aiohttp.ClientTimeout(total=10),
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            ) as response:
                response_text = await response.text()
                request_time = (time.perf_counter() - start_time) * 1000
                logger.debug(f"Temps de la requête pour le Lot {lot}: {request_time:.2f}ms")
                logger.debug(f"Statut de la réponse pour Lot {lot}: {response.status}")
                logger.debug(f"Texte de la réponse: {response_text[:500]}...")
                
                return {
                    'lot': lot,
                    'success': True,
                    'status': response.status,
                    'purchase_times': purchase_time,
                    'response_text': response_text,
                    'duration_ms': f"{request_time:.2f}"
                }
        except Exception as e:
            logger.error(f"Erreur de requête: {str(e)}")
            return {
                'lot': lot,
                'success': False,
                'status': 500,
                'purchase_times': purchase_time,
                'response_text': e,
                'duration_ms': "N/A"
            }
    
    # Lancement simultané des requêtes
    tasks = [make_request() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.perf_counter() - start_time
    logger.info(f"Temps total pour la tentatives du Lot {lot}: {total_time}s")
    
    # if result['success']:
    #     return result

    successful_results = [r for r in results if r['success']]
    if successful_results:
        logger.info(f"Résultats réussis pour le Lot {lot}: {successful_results}")
        fastest_result = min(successful_results, key=lambda x: x['duration_ms'])
        return fastest_result
    
    return {
        'lot': lot,
        'sync_offset_ms': sync_offset * 1000,
        'success': False,
        'error': 'Toutes les tentatives ont échoué'
    }
    
async def perform_timed_purchase_batch(
    base_url: str,
    login: str,
    password: str,
    lots: List[int],
    purchase_times: List[datetime]
) -> List[dict]:
    # Login once to get session and CSRF token
    success, duration, metrics, session, csrf_token = await login_to_website(base_url, login, password)

    if not success:
        logger.error("Login failed. Cannot proceed with purchases.")
        return []

    print(f"\nLogin - Performance Metrics:")
    for operation, duration in metrics.items():
        print(f"{operation}: {duration*1000:.0f}ms")
    print("\nConnexion réussie !\n")

    try:
        purchase_tasks = [perform_synchronized_purchase(session, base_url, csrf_token, lot, password, purchase_times) for lot in lots]
        results = await asyncio.gather(*purchase_tasks)

    except Exception as e:
        logger.error(f"Error in purchase batch: {e}")
        results = []
    finally:
        if session:
            await session.close()

    return results
