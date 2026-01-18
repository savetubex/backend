import re
import yt_dlp
from collections import defaultdict
from validators import URLValidator

ip_usage_counter = defaultdict(int)
ip_view_counter = defaultdict(int)
USAGE_LIMIT = 2
VIEW_LIMIT = 2

class MediaParser:
    def __init__(self):
        self.validator = URLValidator()
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'format': 'best[height<=1080]/best',
        }

    async def parse_url(self, url: str, client_ip: str = None) -> dict:
        if client_ip and ip_usage_counter[client_ip] >= USAGE_LIMIT:
            raise ValueError("LIMIT_REACHED")
        
        self.validator.is_public_url(url)
        platform = self._detect_platform(url)
        
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                self.validator.validate_content_type(info)
                
                if client_ip:
                    ip_usage_counter[client_ip] += 1
                
                return self._format_response(info, platform)
            except Exception as e:
                raise ValueError(f"Failed to extract media info: {str(e)}")

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