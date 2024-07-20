import yt_dlp

def get_video_details(url):
    ydl_opts = {
        'quiet': True,  # Suppress output
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        video_details = {
            'title': info.get('title'),
            'duration': info.get('duration'),
            'is_live': info.get('is_live'),
            'uploader': info.get('uploader'),
            'upload_date': info.get('upload_date'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'dislike_count': info.get('dislike_count'),
            'comment_count': info.get('comment_count'),
            'average_rating': info.get('average_rating'),
        }

    return video_details

# Example usage:
url = 'https://www.youtube.com/watch?v=yJg-Y5byMMw'
details = get_video_details(url)
print(details)