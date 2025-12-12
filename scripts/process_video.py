import os
import glob
import subprocess

def process_video_url(youtube_url, output_dir="data"):
    """
    Downloads subtitles (and audio) from a YouTube URL using yt-dlp.
    Returns the path to the generated SRT file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Base filename pattern
    output_template = os.path.join(output_dir, "requested_transcript.%(ext)s")
    
    # Clean up existing srt/audio files to avoid confusion
    for f in glob.glob(os.path.join(output_dir, "requested_transcript*")):
        try:
            os.remove(f)
        except OSError:
            pass

    # yt-dlp command to get subtitles
    # We prefer manual subtitles (en), then auto-generated (en), then auto-translated.
    cmd = [
        "yt-dlp",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", "en,en-US",
        "--sub-format", "srt",
        "--skip-download", # Don't download video/audio if we just need subs for now
        "-o", output_template,
        youtube_url
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error downloading subtitles: {e}")
        return None

    # yt-dlp might name it requested_transcript.en.srt
    # Find the file
    possible_files = glob.glob(os.path.join(output_dir, "requested_transcript*.srt"))
    if not possible_files:
        return None
    
    # Rename to standard name expected by other scripts
    target_file = os.path.join(output_dir, "requested_transcript.en.srt")
    if possible_files[0] != target_file:
        os.rename(possible_files[0], target_file)
        
    return target_file

if __name__ == "__main__":
    # Test
    url = "https://www.youtube.com/watch?v=mM3mutz432w" # Example from index.html
    print(process_video_url(url))

