from pytube import YouTube
import sys

def download_youtube_video(url):
    print (f"Downloading video..., {url}")
    YouTube(url).streams.first().download()
    yt = YouTube(url)
    yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first().download()
    yt.streams.filter(only_audio=False).first().download()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ytmp4.py <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    try:
        download_youtube_video(url)
    except Exception as e:
        print("Error: ", e)