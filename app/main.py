from fastapi import FastAPI, HTTPException
import requests
import os
import urllib.parse
import logging
import isodate
import redis
import json
import random

api_key = os.getenv('YOUTUBE_API_KEY')
app = FastAPI()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sentinel 구성
sentinel_host = os.getenv('SENTINEL_HOST')
sentinel_port = int(os.getenv('SENTINEL_PORT'))
master_name = os.getenv('SENTINEL_MASTER_NAME')
sentinel = Sentinel([(sentinel_host, sentinel_port)], socket_timeout=0.1)

# Primary (Master) 가져오기
try:
    redis_primary_client = sentinel.master_for(master_name, socket_timeout=0.1)
    master_info = sentinel.discover_master(master_name)
    logger.info(f"Master info: {master_info}")
except Exception as e:
    logger.error(f"Failed to get master: {str(e)}")
    redis_primary_client = None

# Secondary (Replica) 가져오기
try:
    redis_replica_client = sentinel.slave_for(master_name, socket_timeout=0.1)
    logger.info("Connected to replica")
except Exception as e:
    logger.error(f"Failed to get replica: {str(e)}")
    redis_replica_client = None

def get_redis_connection(write=False):
    if write:
        return redis_primary_client
    else:
        if redis_replica_client:
            return redis_replica_client
        else:
            logger.warning("No replicas available, using primary for read")
            return redis_primary_client

# 쇼츠 비디오 판단 함수
def is_short_video(item, duration_seconds):
    title = item['snippet']['title']
    description = item['snippet']['description']
    return duration_seconds <= 60 and ('#shorts' in title.lower() or '#shorts' in description.lower())

# 유튜브 검색 함수
def youtube_search(query, duration, target_count=20):
    encoded_query = urllib.parse.quote(query)
    cache_key = f"youtube_search:{query}:{duration}"

    # 캐시에서 결과 가져오기 (읽기 전용)
    try:
        cached_result = get_redis_connection(write=False).get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for key: {cache_key}")
            return json.loads(cached_result)
    except Exception as e:
        logger.error(f"Failed to get cache: {str(e)}")

    # 유튜브 검색 API 호출
    search_url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"part=snippet&"
        f"type=video&"
        f"q={encoded_query}&"
        f"maxResults=50&"
        f"key={api_key}"
    )
    logger.info(f"Requesting URL: {search_url}")
    search_response = requests.get(search_url)
    if search_response.status_code != 200:
        logger.error(f"Search request failed with status code {search_response.status_code}: {search_response.text}")
        raise HTTPException(status_code=search_response.status_code,
                            detail=f"YouTube API request failed with status code {search_response.status_code}: {search_response.text}")

    search_data = search_response.json()
    logger.info(f"Search response data: {search_data}")
    video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]

    # 비디오 세부 정보 가져오기
    video_details = get_video_details(video_ids, duration, target_count)

    # 결과를 캐시에 저장 (쓰기 전용)
    try:
        logger.info(f"Setting cache for key: {cache_key} with data: {json.dumps(video_details)}")
        get_redis_connection(write=True).setex(cache_key, 3600, json.dumps(video_details))
    except Exception as e:
        logger.error(f"Failed to set cache: {str(e)}")

    return video_details

# 비디오 세부 정보 가져오기 함수
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
    logger.info(f"Details response data: {details_data}")

    videos = []

    for item in details_data.get('items', []):
        video_id = item['id']
        title = item['snippet']['title']
        duration_iso = item['contentDetails']['duration']
        duration_seconds = parse_duration(duration_iso)

        if duration == "short" and is_short_video(item, duration_seconds):
            videos.append({
                'video_id': video_id,
                'title': title,
            })
        elif duration == "long" and duration_seconds > 60:
            videos.append({
                'video_id': video_id,
                'title': title,
            })

        if len(videos) >= target_count:
            break

    return videos

# ISO 8601 duration을 초 단위로 변환하는 함수
def parse_duration(duration):
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
    uvicorn.run(app, host="0.0.0.0", port=5000)