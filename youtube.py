import yt_dlp

def get_video_information(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True, 
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        
            print(f"\nTitle: {info.get('title')}\nChannel: {info.get('uploader')}\nDuration: {info.get('duration')} seconds")
            print(f"View Count: {info.get('view_count')}\nResolution: {info.get('width')}x{info.get('height')}\nUpdate Date: {info.get('upload_date')}")
            print(f"Description: {info.get('description')[:200] + "..."}")

            formats = info.get('formats', [])
            resolutions = set()

            for f in formats:
                if f.get('height') and int(f.get('height')) >= 360:
                    resolutions.add(f.get('height'))

            sorted_res = sorted(list(resolutions), reverse=True)
            print(f"\nSupported resolutions for: {info.get('title')}")
            for res in sorted_res:
                print(f"- {res}p")

            return resolutions

        except Exception as e:
            return {"Error": str(e)}


def download_video(url, quality):
    ydl_opts = {
        
        'format': 'bestvideo[height<=' + quality + ']+bestaudio/best',
        'merge_output_format': 'mkv',
        
        'outtmpl': '%(title)s.%(ext)s',
        
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Starting download: {url}")
            ydl.download([url])
            print("Download and merge complete!\n")
    except Exception as e:
        print(f"Error occurred: {e}")



def download_audio(url):

    ydl_opts = {
        'format': 'bestaudio/best', 

        'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320', 
    }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            print(f"Title: {info.get('title')}")
            print(f"Uploader: {info.get('uploader')}")
            print(f"Duration: {info.get('duration')} seconds")
            
            ydl.download([url])

            print("\nSuccessfully downloaded and converted to MP3!")
    except Exception as e:
        print(f"\nAn error occurred: {e}")



if __name__ == "__main__":

    BANNER = r"""
_________  ___  ___  ________   _______           _________  ___  ___  ________  _______      
|\___   ___\\  \|\  \|\   ___  \|\  ___ \         |\___   ___\\  \|\  \|\   __  \|\  ___ \     
\|___ \  \_\ \  \\\  \ \  \\ \  \ \   __/|        \|___ \  \_\ \  \\\  \ \  \|\  \ \   __/|    
     \ \  \ \ \  \\\  \ \  \\ \  \ \  \_|/__           \ \  \ \ \  \\\  \ \   __  \ \  \_|/__  
      \ \  \ \ \  \\\  \ \  \\ \  \ \  \_|\ \           \ \  \ \ \  \\\  \ \  \|\  \ \  \_|\ \ 
       \ \__\ \ \_______\ \__\\ \__\ \_______\           \ \__\ \ \_______\ \_______\ \_______\
        \|__|  \|_______|\|__| \|__|\|_______|            \|__|  \|_______|\|_______|\|_______|
                                                                                               
                            >> HIGH QUALITY MEDIA EXTRACTION ENGINE <<
"""
    print(BANNER)
    print("\n")

    url = input("Enter the video URL: ")

    option = input("Do you want do download Video/Audio ('1' : Audio, '2': Video): ")

    if option == '2':
        resolution = get_video_information(url)
        quality = input("Enter the resolution of the video (digits only, eg: 1080, 1440,..): ")
        if quality.isdigit() and int(quality) >= 360:
            download_video(url, quality)
        else:
            print("Invalid resolution.")  
    elif option == '1':
        download_audio(url)
    else:
        print("\nInvalid Option\n")
    