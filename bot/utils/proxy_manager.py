import json
from typing import Optional, Dict
from bot.config import settings
from bot.utils.logger import logger
from pathlib import Path

class ProxyManager:
    def __init__(self):
        self.proxies = {}
        self.base_dir = Path(__file__).parent.parent.parent
        self.accounts_file = self.base_dir / "sessions" / "accounts.json"

    async def init_proxies(self):
        """Инициализирует прокси из accounts.json"""
        try:
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
            
            logger.info(f"Reading accounts from: {self.accounts_file}")
            
            for account in accounts:
                session_name = account["session_name"]
                proxy = account["proxy"]
                formatted_proxy = f"{settings.proxy_type}://{proxy}"
                self.proxies[session_name] = formatted_proxy
                
            logger.info(f"Loaded {len(self.proxies)} proxies from accounts.json")
            return self.proxies
                
        except FileNotFoundError:
            logger.warning(f"Accounts file not found at: {self.accounts_file}")
            return {}
        except Exception as e:
            logger.error(f"Error loading proxies: {e}")
            return {}

    def get_proxy(self, session_name: str) -> Optional[str]:
        """Получает прокси для сессии"""
        proxy = self.proxies.get(session_name)
        if proxy:
            parts = proxy.split('@')[-1].split(':')
            if len(parts) >= 2:
                return f"bind {parts[-2]}:{parts[-1]}"
        return None

proxy_manager = ProxyManager()