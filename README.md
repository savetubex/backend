# SaveTubeX Backend

FastAPI backend for parsing public social media URLs and extracting metadata.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API

### POST /api/parse

Extract metadata from public media URLs.

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=..."
}
```

**Response:**
```json
{
  "platform": "youtube",
  "title": "Video Title",
  "thumbnail": "https://...",
  "formats": [
    {
      "quality": "1080p",
      "url": "https://direct-media-url"
    }
  ]
}
```

## Supported Platforms

- YouTube
- Instagram (public posts only)
- Facebook (public posts only)

## Rate Limiting

10 requests per minute per IP address.