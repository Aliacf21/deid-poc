import re
import textwrap

def clean_srt(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove line numbers
    content = re.sub(r'^\d+$', '', content, flags=re.MULTILINE)
    # Remove timestamps
    content = re.sub(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', '', content)
    
    lines = content.split('\n')
    clean_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            clean_lines.append(line)
            
    # Simple adjacent deduplication for auto-subs which often repeat lines
    final_lines = []
    if clean_lines:
        final_lines.append(clean_lines[0])
        for i in range(1, len(clean_lines)):
            if clean_lines[i] != clean_lines[i-1]:
                final_lines.append(clean_lines[i])

    transcript = ' '.join(final_lines)
    # Wrap text at 80 characters
    wrapped_transcript = textwrap.fill(transcript, width=80)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(wrapped_transcript)

if __name__ == "__main__":
    clean_srt('requested_transcript.en.srt', 'requested_transcript.txt')
