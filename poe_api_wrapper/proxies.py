import time
import random
from typing import Dict, List, Optional
import requests
from threading import Lock

try:
    from ballyregan import ProxyFetcher
    from ballyregan.models import Protocols, Anonymities
    PROXY = True
except ImportError as e:
    print(f"Skipping ProxyFetcher due to {e}.")
    PROXY = False

class ProxyManager:
    def __init__(self, cooldown_time: int = 60):
        self.proxies: List[Dict] = []
        self.proxy_status: Dict[str, Dict] = {}  # Tracks last use time and failure count
        self.cooldown_time = cooldown_time  # Time in seconds before reusing a proxy
        self.lock = Lock()
        self.refresh_proxies()
    
    def refresh_proxies(self) -> None:
        """Fetch new proxies and validate them"""
        if not PROXY:
            return
        
        fetcher = ProxyFetcher()
        try:
            # Try to get anonymous proxies first
            proxy_list = fetcher.get(
                limit=20,  # Increased limit for better rotation
                protocols=[Protocols.HTTP, Protocols.HTTPS],
                anonymities=[Anonymities.ANONYMOUS],
            )
        except Exception:
            try:
                # Fall back to any proxies if anonymous ones aren't available
                print("No Anonymous proxies found. Switching to normal proxies...")
                proxy_list = fetcher.get(
                    limit=20,
                    protocols=[Protocols.HTTP, Protocols.HTTPS],
                )
            except Exception as e:
                print(f"Failed to fetch proxies: {e}")
                return

        new_proxies = []
        for proxy in proxy_list:
            proxy_dict = {
                'http': f'http://{proxy.ip}:{proxy.port}',
                'https': f'http://{proxy.ip}:{proxy.port}'
            }
            # Validate proxy
            if self._test_proxy(proxy_dict):
                new_proxies.append(proxy_dict)
        
        with self.lock:
            self.proxies = new_proxies
            # Initialize status for new proxies
            for proxy in new_proxies:
                proxy_key = str(proxy)
                if proxy_key not in self.proxy_status:
                    self.proxy_status[proxy_key] = {
                        'last_used': 0,
                        'failures': 0
                    }

    def _test_proxy(self, proxy: Dict) -> bool:
        """Test if proxy is working"""
        try:
            response = requests.get(
                'https://api.poe.com',  # Use actual API endpoint for testing
                proxies=proxy,
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

    def get_proxy(self) -> Optional[Dict]:
        """Get a proxy that's not in cooldown and hasn't failed too much"""
        if not self.proxies:
            self.refresh_proxies()
            if not self.proxies:
                return None

        current_time = time.time()
        available_proxies = []

        with self.lock:
            for proxy in self.proxies:
                proxy_key = str(proxy)
                status = self.proxy_status[proxy_key]
                
                # Skip proxies that are in cooldown or have failed too many times
                if (current_time - status['last_used'] < self.cooldown_time or 
                    status['failures'] >= 3):
                    continue
                    
                available_proxies.append(proxy)

            if not available_proxies:
                # If no proxies are available, refresh the list
                self.refresh_proxies()
                return self.get_proxy()

            # Choose a random proxy from available ones
            chosen_proxy = random.choice(available_proxies)
            self.proxy_status[str(chosen_proxy)]['last_used'] = current_time
            return chosen_proxy

    def mark_proxy_failed(self, proxy: Dict) -> None:
        """Mark a proxy as failed"""
        with self.lock:
            proxy_key = str(proxy)
            if proxy_key in self.proxy_status:
                self.proxy_status[proxy_key]['failures'] += 1
                # Remove proxy if it has failed too many times
                if self.proxy_status[proxy_key]['failures'] >= 3:
                    self.proxies = [p for p in self.proxies if str(p) != proxy_key]

# Global proxy manager instance
proxy_manager = ProxyManager()

def get_proxy() -> Optional[Dict]:
    """Get a proxy from the proxy manager"""
    return proxy_manager.get_proxy() if PROXY else None

def mark_proxy_failed(proxy: Dict) -> None:
    """Mark a proxy as failed in the proxy manager"""
    if PROXY:
        proxy_manager.mark_proxy_failed(proxy)