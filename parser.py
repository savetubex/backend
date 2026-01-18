import re
import yt_dlp
import random
import time
import httpx
import json
from collections import defaultdict
from validators import URLValidator

ip_usage_counter = defaultdict(int)
ip_view_counter = defaultdict(int)
USAGE_LIMIT = 2
VIEW_LIMIT = 2

class MediaParser:
    def __init__(self):
        self.validator = URLValidator()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
    def _get_ydl_opts(self):
        return {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'format': 'best[height<=720]/best',
            'http_headers': {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Cache-Control': 'max-age=0'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['hls', 'dash', 'translated_subs'],
                    'player_skip': ['configs', 'webpage'],
                    'comment_sort': ['top'],
                    'max_comments': [0]
                }
            },
            'sleep_interval': 2,
            'max_sleep_interval': 5,
            'socket_timeout': 30,
            'retries': 3
        }

    async def parse_url(self, url: str, client_ip: str = None) -> dict:
        if client_ip and ip_usage_counter[client_ip] >= USAGE_LIMIT:
            raise ValueError("LIMIT_REACHED")
        
        self.validator.is_public_url(url)
        platform = self._detect_platform(url)
        
        # Try fallback method first for YouTube
        if platform == 'youtube':
            try:
                return await self._youtube_fallback(url, client_ip)
            except:
                pass  # Continue to yt-dlp method
        
        max_retries = 5
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(3, 8) * (attempt + 1)
                    time.sleep(delay)
                
                with yt_dlp.YoutubeDL(self._get_ydl_opts()) as ydl:
                    info = ydl.extract_info(url, download=False)
                    self.validator.validate_content_type(info)
                    
                    if client_ip:
                        ip_usage_counter[client_ip] += 1
                    
                    return self._format_response(info, platform)
                    
            except Exception as e:
                error_msg = str(e).lower()
                if attempt == max_retries - 1:
                    if any(keyword in error_msg for keyword in ['sign in', 'bot', 'captcha', 'verify']):
                        raise ValueError("Service temporarily unavailable. YouTube is blocking automated requests from this server.")
                    elif 'private' in error_msg:
                        raise ValueError("This video is private or requires authentication")
                    elif any(keyword in error_msg for keyword in ['unavailable', 'removed', 'deleted']):
                        raise ValueError("Video is unavailable or has been removed")
                    elif 'age' in error_msg:
                        raise ValueError("Age-restricted content cannot be accessed")
                    else:
                        raise ValueError(f"Unable to process video: Please try again later")
                continue

    def _detect_platform(self, url: str) -> str:
        if 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'instagram.com' in url:
            return 'instagram'
        elif 'facebook.com' in url or 'fb.watch' in url:
            return 'facebook'
        else:
            raise ValueError("Unsupported platform")

    def _format_response(self, info: dict, platform: str) -> dict:
        video_formats = []
        audio_formats = []
        images = []
        seen_video_qualities = set()
        seen_audio_qualities = set()
        
        if info.get('formats'):
            progressive_formats = []
            for fmt in info['formats']:
                if (fmt.get('url') and 
                    fmt.get('ext') == 'mp4' and 
                    fmt.get('protocol') == 'https' and 
                    fmt.get('acodec') != 'none' and 
                    fmt.get('vcodec') != 'none'):
                    progressive_formats.append(fmt)
            
            if len(progressive_formats) < 3:
                for fmt in info['formats']:
                    if (fmt.get('url') and 
                        fmt.get('ext') == 'mp4' and 
                        'manifest' not in fmt.get('url', '').lower() and
                        '.m3u8' not in fmt.get('url', '').lower()):
                        progressive_formats.append(fmt)
            
            sorted_video_formats = sorted(
                progressive_formats,
                key=lambda x: x.get('height') or 0,
                reverse=True
            )
            
            for fmt in sorted_video_formats:
                if len(video_formats) >= 6:
                    break
                quality = self._get_quality_label(fmt)
                if quality not in seen_video_qualities and quality != 'unknown':
                    seen_video_qualities.add(quality)
                    video_formats.append({
                        'quality': quality,
                        'url': fmt['url'],
                        'type': 'video'
                    })
            
            for fmt in info['formats']:
                if (fmt.get('url') and 
                    fmt.get('acodec') != 'none' and 
                    fmt.get('vcodec') == 'none' and 
                    fmt.get('ext') in ['m4a', 'mp4']):
                    quality = f"Audio ({fmt.get('ext', 'M4A').upper()})"
                    if quality not in seen_audio_qualities:
                        seen_audio_qualities.add(quality)
                        audio_formats.append({
                            'quality': quality,
                            'url': fmt['url'],
                            'type': 'audio'
                        })
                        if len(audio_formats) >= 2:
                            break
        
        if info.get('thumbnails'):
            for thumb in info['thumbnails'][-3:]:
                if thumb.get('url'):
                    label = f"Thumbnail {thumb.get('width', 'HD')}x{thumb.get('height', '')}"
                    images.append({
                        'label': label,
                        'url': thumb['url']
                    })
        
        all_formats = video_formats + audio_formats
        
        return {
            'platform': platform,
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'formats': all_formats,
            'images': images
        }

    def _get_quality_label(self, fmt: dict) -> str:
        if fmt.get('height'):
            return f"{fmt['height']}p"
        
        if fmt.get('format_note'):
            format_note = fmt['format_note'].lower()
            if '1080' in format_note:
                return '1080p'
            elif '720' in format_note:
                return '720p'
            elif '480' in format_note:
                return '480p'
            elif '360' in format_note:
                return '360p'
            elif '240' in format_note:
                return '240p'
            elif '144' in format_note:
                return '144p'
            else:
                return format_note
        
        if fmt.get('format_id'):
            format_id = fmt['format_id'].lower()
            if '1080' in format_id:
                return '1080p'
            elif '720' in format_id:
                return '720p'
            elif '480' in format_id:
                return '480p'
            elif '360' in format_id:
                return '360p'
            elif '240' in format_id:
                return '240p'
            elif '144' in format_id:
                return '144p'
        
        if fmt.get('resolution'):
            resolution = fmt['resolution']
            if 'x' in resolution:
                try:
                    height = int(resolution.split('x')[1])
                    return f"{height}p"
                except (ValueError, IndexError):
                    pass
        
        return fmt.get('format_note', 'unknown')
    
    async def _youtube_fallback(self, url: str, client_ip: str = None) -> dict:
        """Fallback method using YouTube embed API"""
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.youtube.com/'
        }
        
        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            # Try embed page
            embed_url = f"https://www.youtube.com/embed/{video_id}"
            response = await client.get(embed_url)
            
            if response.status_code == 200:
                html = response.text
                
                # Extract title
                title_match = re.search(r'"title":"([^"]+)"', html)
                title = title_match.group(1) if title_match else "YouTube Video"
                
                # Extract thumbnail
                thumb_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
                if client_ip:
                    ip_usage_counter[client_ip] += 1
                
                return {
                    'platform': 'youtube',
                    'title': title.replace('\\u0026', '&').replace('\\', ''),
                    'thumbnail': thumb_url,
                    'formats': [{
                        'quality': 'YouTube Link',
                        'url': url,
                        'type': 'video'
                    }],
                    'images': [{
                        'label': 'Thumbnail',
                        'url': thumb_url
                    }]
                }
        
        raise ValueError("Could not access video")
    
    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
