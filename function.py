import aiohttp
import asyncio
import time
import logging
import json
from typing import List, Tuple, Optional, Dict
from collections import defaultdict
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urljoin
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class LoginError(Exception):
    pass

@asynccontextmanager
async def get_optimized_session(timeout: float):
    """Create an optimized aiohttp session with connection pooling"""
    timeout_obj = aiohttp.ClientTimeout(total=timeout, connect=0.5, sock_connect=2.0, sock_read=1.5)
    conn = aiohttp.TCPConnector(
        limit=20,  # Increased concurrent connections
        ttl_dns_cache=3600,  # Increased DNS cache duration
        use_dns_cache=True,
        force_close=False,
        keepalive_timeout=30,
        ssl=False,               # Désactiver la vérification SSL si nécessaire
        enable_cleanup_closed=True
    )

    session = aiohttp.ClientSession(
        connector=conn,
        timeout=timeout_obj,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive'
        },
        cookie_jar=aiohttp.CookieJar(unsafe=True)  # Optimized cookie handling
    )

    try:
        yield session
    finally:
        pass

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
    """Perform concurrent purchase attempts and return first successful result"""
    purchase_url = urljoin(base_url, 'achat/action')

    async def single_purchase_attempt():
        start_time = time.perf_counter()
        purchase_data = {
            'ceo_csrf_token': csrf_token,
            'lot': str(lot),
            'code': buyer_code
        }

        try:
            async with session.post(purchase_url, data=purchase_data) as response:
                response_text = await response.text()
                success = response.status == 200 and 'success' in response_text.lower()
                request_time = (time.perf_counter() - start_time) * 1000  # ms

                return {
                    'success': success,
                    'response_text': response_text,
                    'duration_ms': request_time
                }
        except Exception as e:
            logger.error(f"Purchase attempt error for Lot {lot}: {e}")
            return {
                'success': False,
                'response_text': str(e),
                'duration_ms': (time.perf_counter() - start_time) * 1000
            }

    # Create multiple concurrent tasks
    tasks = [single_purchase_attempt() for _ in range(attempts)]

    # Wait for first successful result
    results = await asyncio.gather(*tasks)
    for result in results:
        try:
            # Tente de parser response_text comme du JSON
            json.loads(result['response_text']) # Si le parsing réussit, c'est du JSON valide
            print(result)
            return result
        except json.JSONDecodeError:
            continue# Si une erreur se produit lors du parsing, ce n'est pas du JSON valide

    return None

async def perform_synchronized_purchase(
    session: aiohttp.ClientSession,
    base_url: str,
    csrf_token: str,
    lot: int,
    password: str,
    purchase_time: datetime
) -> dict:
    # Wait until just before purchase time
    wait_time = max(0, (purchase_time - datetime.now()).total_seconds() - 0.1)
    await asyncio.sleep(wait_time)

    # Perform concurrent purchases
    purchase_result = await perform_concurrent_purchases(
        session, base_url, csrf_token, lot, password
    )

    result = {
        'lot': lot,
        'duration_ms': purchase_result['duration_ms'],
        'success': purchase_result is not None,
        'details': purchase_result
    }
    
    logger.info(f"Purchase for Lot {lot}: {'Success' if purchase_result else 'Failure'}")
    return result

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
        purchase_tasks = []
        for lot in lots:
            # Create a task that waits and then performs purchases
            task = asyncio.create_task(perform_synchronized_purchase(
                session, base_url, csrf_token, lot, password, purchase_times
            ))
            purchase_tasks.append(task)

        # Wait for all purchase tasks to complete
        results = await asyncio.gather(*purchase_tasks)

    except Exception as e:
        logger.error(f"Error in purchase batch: {e}")
        results = []
    finally:
        if session:
            await session.close()

    return results
