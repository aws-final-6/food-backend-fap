from fastapi import FastAPI, HTTPException
import requests
from dotenv import load_dotenv
import os
import urllib.parse
import logging
import isodate

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv('YOUTUBE_API_KEY')
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_short_video(item, duration_seconds):
    title = item['snippet']['title']
    description = item['snippet']['description']

    # 제목 또는 설명란에 #shorts가 들어가고 1분 이하의 영상
    if duration_seconds <= 60 and ('#shorts' in title.lower() or '#shorts' in description.lower()):
        return True
    return False

def youtube_search(query, duration, target_count=20):
    max_results = 50  # 한 번에 최대 50개의 결과를 가져옴
    encoded_query = urllib.parse.quote(query)

    search_url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"part=snippet&"
        f"type=video&"
        f"q={encoded_query}&"
        f"maxResults={max_results}&"
        f"key={api_key}"
    )
    logger.info(f"Requesting URL: {search_url}")
    search_response = requests.get(search_url)
    if search_response.status_code != 200:
        logger.error(f"Search request failed with status code {search_response.status_code}: {search_response.text}")
        raise HTTPException(status_code=search_response.status_code,
                            detail=f"YouTube API request failed with status code {search_response.status_code}: {search_response.text}")

    search_data = search_response.json()
    logger.info(f"Search response data: {search_data}")  # 전체 검색 응답 데이터를 로그에 출력
    video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]

    video_details = get_video_details(video_ids, duration, target_count)

    return video_details

def get_video_details(video_ids, duration, target_count):
    if not video_ids:
        return []

    details_url = (
        f"https://www.googleapis.com/youtube/v3/videos?"
        f"part=snippet,contentDetails&"
        f"id={','.join(video_ids)}&"
        f"key={api_key}"
    )
    details_response = requests.get(details_url)
    if details_response.status_code != 200:
        logger.error(f"Details request failed with status code {details_response.status_code}: {details_response.text}")
        raise HTTPException(status_code=details_response.status_code,
                            detail=f"YouTube API request failed with status code {details_response.status_code}: {details_response.text}")

    details_data = details_response.json()
    logger.info(f"Details response data: {details_data}")  # 전체 비디오 세부 정보 응답 데이터를 로그에 출력
    short_videos = []
    long_videos = []

    for item in details_data.get('items', []):
        video_id = item['id']
        title = item['snippet']['title']
        description = item['snippet']['description']
        channel_title = item['snippet']['channelTitle']
        publish_time = item['snippet']['publishedAt']
        duration_iso = item['contentDetails']['duration']
        duration_seconds = parse_duration(duration_iso)

        if duration == "short" and is_short_video(item, duration_seconds):
            short_videos.append({
                'video_id': video_id,
                'title': title,
                'description': description,
                'channel_title': channel_title,
                'publish_time': publish_time,
                'duration': duration_seconds
            })
        elif duration == "long" and duration_seconds > 60:
            long_videos.append({
                'video_id': video_id,
                'title': title,
                'description': description,
                'channel_title': channel_title,
                'publish_time': publish_time,
                'duration': duration_seconds
            })

        if len(short_videos) >= target_count and len(long_videos) >= target_count:
            break

    if duration == "short":
        return short_videos[:target_count]
    elif duration == "long":
        return long_videos[:target_count]

def parse_duration(duration):
    # ISO 8601 duration을 초 단위로 변환하는 함수
    duration_obj = isodate.parse_duration(duration)
    return int(duration_obj.total_seconds())

@app.get("/api/video/long")
def search_long_videos():
    return youtube_search(query="레시피", duration="long")

@app.get("/api/video/short")
def search_short_videos():
    return youtube_search(query="레시피", duration="short")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)