import time
from collections import defaultdict
from typing import Dict, List

class AbuseMonitor:
    def __init__(self):
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: set = set()
        self.suspicious_patterns = [
            'bot', 'crawler', 'scraper', 'automated'
        ]
    
    def is_suspicious_request(self, ip: str, user_agent: str = '') -> bool:
        """Check if request shows signs of abuse"""
        current_time = time.time()
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            return True
        
        # Check user agent for suspicious patterns
        if any(pattern in user_agent.lower() for pattern in self.suspicious_patterns):
            return True
        
        # Check request frequency (more than 10 requests in 1 minute)
        recent_requests = [
            req_time for req_time in self.request_history[ip]
            if current_time - req_time < 60
        ]
        
        if len(recent_requests) > 10:
            self.blocked_ips.add(ip)
            return True
        
        # Log this request
        self.request_history[ip].append(current_time)
        
        # Clean old requests (older than 1 hour)
        self.request_history[ip] = [
            req_time for req_time in self.request_history[ip]
            if current_time - req_time < 3600
        ]
        
        return False
    
    def get_stats(self) -> dict:
        """Get monitoring statistics"""
        return {
            'blocked_ips': len(self.blocked_ips),
            'active_ips': len(self.request_history),
            'total_requests': sum(len(requests) for requests in self.request_history.values())
        }