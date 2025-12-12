import os
import re

def parse_srt(file_path, include_timestamps=True):
    """
    Parses an SRT file and returns the transcript text.
    
    Args:
        file_path (str): Path to the .srt file.
        include_timestamps (bool): If True, embeds [T=seconds] markers before each block.
                                   If False, returns clean text joined by spaces.
    
    Returns:
        str: The parsed transcript text, or None/empty string if file not found.
    """
    if not os.path.exists(file_path):
        return "" if include_timestamps else None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to extract timestamp and text block
    # Matches: Index, Time Range, Text content
    pattern = re.compile(r'(\d+)?\n?(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
    matches = pattern.findall(content)
    
    if include_timestamps:
        formatted_transcript = ""
        for match in matches:
            # Match indices change depending on if the optional (\d+)? captured something or not
            # But standard SRT always has index. Let's rely on the structure.
            # findall with groups returns tuple.
            # If (\d+)? is group 1, time is 2, time_end is 3, content is 4.
            
            # Handling potential optional group match issues by checking tuple length or non-empty
            # In standard regex above: 
            # 1: Index (optional in my regex but usually present)
            # 2: Start Time
            # 3: End Time
            # 4: Content
            
            start_time_str = match[1]
            text_content = match[3].replace('\n', ' ').strip()
            
            # Convert HH:MM:SS,mmm to total seconds
            h, m, s = start_time_str.replace(',', '.').split(':')
            total_seconds = int(int(h) * 3600 + int(m) * 60 + float(s))
            
            formatted_transcript += f"[T={total_seconds}] {text_content} "
        return formatted_transcript
    else:
        # Plain text mode (Visual Map style)
        formatted_transcript = []
        for match in matches:
            text_content = match[3].replace('\n', ' ').strip()
            # Cleanup common SRT artifacts if needed (like ">>" or speaker names if regex didn't catch)
            clean_text = re.sub(r'^[A-Z\s]+:', '', text_content)
            if clean_text:
                formatted_transcript.append(clean_text)
        return " ".join(formatted_transcript)

