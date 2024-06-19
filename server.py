from fastapi import FastAPI
import requests
import datetime
import re

api_key = 'your key'
app = FastAPI()

def time_to_sec(duration):
    pattern = re.compile(
        r'P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?'
        r'T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?'
    )
    match = pattern.match(duration)
    if not match:
        return 0
    duration_dict = match.groupdict()
    for key, value in duration_dict.items():
        duration_dict[key] = int(value) if value else 0
    total_seconds = (
        duration_dict['years'] * 31536000 +
        duration_dict['months'] * 2592000 +
        duration_dict['days'] * 86400 +
        duration_dict['hours'] * 3600 +
        duration_dict['minutes'] * 60 +
        duration_dict['seconds']
    )
    return total_seconds

def youtube_search(query, duration, max_results=20):
    # Calculate the date 3 days ago in ISO 8601 format
    three_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).isoformat()
    
    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={query}&maxResults={max_results}&publishedAfter={three_days_ago}&key={api_key}"
    search_response = requests.get(search_url)
    
    if search_response.status_code == 200:
        search_data = search_response.json()
        video_details = []

        for item in search_data['items']:
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            # Get video duration
            video_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={api_key}"
            video_response = requests.get(video_url)
            
            if video_response.status_code == 200:
                video_data = video_response.json()
                video_length = video_data['items'][0]['contentDetails']['duration']
                video_time = time_to_sec(video_length)
                if duration == "long" and video_time > 60:
                    video_details.append({
                        'video_id': video_id,
                        'title': title,
                        'duration': video_length
                    })
                elif duration == "short" and video_time <= 60:
                    video_details.append({
                        'video_id': video_id,
                        'title': title,
                        'duration': video_length
                    })
        print(video_details)
        return video_details
    else:
        print(f"Error: Unable to perform search. Status code: {search_response.status_code}")
        return None

@app.get("/api/video/long")
def search_videos():
    return youtube_search(query="레시피", duration="long")

@app.get("/api/video/shorts")
def search_short_videos():
    return youtube_search(query="레시피", duration="short")
