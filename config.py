#!/usr/bin/env python3
"""
Configuration for Google Maps Scraper
"""

import os
from typing import Dict, Optional
import random


class ScraperConfig:
    """Main configuration class."""
    
    # Proxy settings
    USE_PROXIES = True
    
    # User agents for rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    @classmethod
    def get_random_user_agent(cls) -> str:
        """Get a random user agent."""
        return random.choice(cls.USER_AGENTS)


class ProxyConfig:
    """Proxy configuration and management."""
    
    def __init__(self):
        self.proxies = self._load_proxies()
    
    def _load_proxies(self) -> list:
        """Load proxies from environment or file."""
        # Try to load from environment variable
        proxies_str = os.getenv('PROXIES', '')
        if proxies_str:
            return [p.strip() for p in proxies_str.split(',') if p.strip()]
        
        # Try to load from file
        try:
            with open('proxies.txt', 'r') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            pass
        
        return []
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random proxy from the list."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def _parse_proxy_url(self, proxy_url: str) -> Dict:
        """
        Parse proxy URL into Playwright format.
        
        Args:
            proxy_url: Proxy in format http://user:pass@host:port or http://host:port
            
        Returns:
            Dict with server, username, password
        """
        if not proxy_url:
            return None
        
        try:
            # Remove protocol
            if '://' in proxy_url:
                protocol, rest = proxy_url.split('://', 1)
            else:
                protocol = 'http'
                rest = proxy_url
            
            # Parse auth if present
            if '@' in rest:
                auth, server = rest.split('@', 1)
                if ':' in auth:
                    username, password = auth.split(':', 1)
                else:
                    username = auth
                    password = ''
            else:
                server = rest
                username = None
                password = None
            
            proxy_dict = {
                'server': f'{protocol}://{server}'
            }
            
            if username:
                proxy_dict['username'] = username
            if password:
                proxy_dict['password'] = password
            
            return proxy_dict
            
        except Exception as e:
            print(f"Error parsing proxy URL: {e}")
            return None


# Global instances
proxy_config = ProxyConfig()


# Print configuration on import
if __name__ != '__main__':
    if not ScraperConfig.USE_PROXIES:
        print("⚠️ PROXY DISABLED FOR TESTING")
    else:
        proxy_count = len(proxy_config.proxies)
        if proxy_count > 0:
            print(f"✓ Loaded {proxy_count} proxies")
        else:
            print("⚠️ No proxies loaded")
