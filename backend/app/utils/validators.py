import re
from urllib.parse import urlparse

class URLValidator:
    def __init__(self):
        self.private_patterns = [
            r'private',
            r'login',
            r'signin',
            r'auth',
            r'/p/',  # Instagram private posts
            r'story',  # Instagram stories
            r'reel/.*private',
            r'account/login',
            r'members-only',
            r'subscriber',
        ]
        
        self.supported_domains = [
            'youtube.com',
            'youtu.be',
            'instagram.com',
            'facebook.com',
            'fb.watch'
        ]
        
        self.blocked_patterns = [
            r'live',  # Live streams
            r'premiere',  # Premieres
            r'shorts/.*private',
            r'channel/.*private',
        ]

    def is_public_url(self, url: str) -> bool:
        parsed = urlparse(url)
        
        # Check if domain is supported
        if not any(domain in parsed.netloc for domain in self.supported_domains):
            raise ValueError("Unsupported platform")
        
        # Check for private content patterns
        for pattern in self.private_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("Private or login-required URLs not supported")
        
        # Check for blocked content types
        for pattern in self.blocked_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                raise ValueError("Live streams and premieres not supported")
        
        return True

    def validate_content_type(self, info: dict) -> bool:
        """Additional validation based on extracted metadata"""
        if info.get('is_live'):
            raise ValueError("Live content not supported")
        
        if info.get('availability') == 'private':
            raise ValueError("Private content not accessible")
            
        return True