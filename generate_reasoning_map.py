import os
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure API - Using available model
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- 1. ROBUST SRT PARSER ---
def parse_srt(file_path):
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to extract timestamp and text block
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:(?!\n\n).)*)', re.DOTALL)
    matches = pattern.findall(content)
    
    formatted_transcript = []
    
    for match in matches:
        text_content = match[2].replace('\n', ' ').strip()
        # We strip speaker tags if they are generic like ">>" to save tokens
        clean_text = re.sub(r'^[A-Z\s]+:', '', text_content) 
        if clean_text:
            formatted_transcript.append(clean_text)
            
    return " ".join(formatted_transcript)

# --- 2. THE "WISDOM TOPOLOGY" PROMPT ---
def generate_reasoning_map(full_transcript_text):
    # We use gemini-2.5-pro as it is the available high-reasoning model for this environment
    model = genai.GenerativeModel('gemini-2.5-pro')

    prompt = f"""
### ROLE
You are a Medical Illustrator and Educator creating a "Clinical Reasoning Flowchart" for a medical journal.
Your goal is clarity, readability, and logical flow.

### INPUT TRANSCRIPT
{full_transcript_text}

### OBJECTIVE
Visualize the Grand Rounds case as a logical journey from **Presentation** -> **Differential Debate** -> **Diagnosis**.
The map must be immediately understandable to a human reader. Avoid abstract labels. Use concrete clinical terms.

### MERMAID ARCHITECTURE
**Orientation:** `graph TD` (Top-Down Flow) for better readability on standard screens.

**Structure the graph into 3 Logical Phases (Subgraphs):**

1.  `subgraph Phase_1 [The Clinical Puzzle]`
    *   **Patient Profile:** Age, Gender, History (e.g., "46M, Atrial Pseudoaneurysm").
    *   **Key Findings:** The specific symptoms driving the confusion (e.g., "Chest Pain + Halo Sign").
    *   **The Hook:** Why is this hard? (e.g., "Multi-system involvement").

2.  `subgraph Phase_2 [The Differential Debate]`
    *   **The Main Question:** e.g., "Infection vs. Malignancy?"
    *   **Hypothesis 1 (Infectious):** List the specific bugs considered (e.g., "Fungal, TB, Nocardia").
    *   **Hypothesis 2 (Malignancy):** List the cancer types considered (e.g., "Lymphoma, Sarcoma").
    *   **The Turning Point:** What specific thought or finding shifted the tide? (e.g., "Negative Cultures" or "Biopsy Result").

3.  `subgraph Phase_3 [Resolution & Wisdom]`
    *   **Final Diagnosis:** The answer (e.g., "Cardiac Angiosarcoma").
    *   **Teaching Point:** The main takeaway lesson (e.g., "Angiosarcoma can mimic infectious pericarditis").

### FORMATTING RULES (CRITICAL)
1.  **Quote ALL Node Labels:** e.g., `A("Patient 46M")` NOT `A(Patient 46M)`. This prevents syntax errors with special characters.
2.  **Concise Text:** Keep node text under 6-8 words. Use `<br>` for line breaks if needed.
3.  **No Special Characters in IDs:** Use `Node1` or `Hypothesis_A`. Do not use `Node-1` or `Node(1)`.
4.  **Styling:**
    *   Use `classDef` to color code the three phases distinctively.
    *   Phase 1: Blue/Info styling.
    *   Phase 2: Orange/Action styling.
    *   Phase 3: Green/Success styling.

### OUTPUT FORMAT
Return **ONLY** the raw Mermaid definition text. Start strictly with `graph TD`. 
Do not use markdown ticks.
"""

    try:
        print("Sending prompt to Gemini...")
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```mermaid', '').replace('```', '').strip()
        return clean_text
    except Exception as e:
        print(f"Error generating map: {e}")
        return None

# --- 3. HTML GENERATOR WITH ZOOM UI ---
def create_interactive_html(mermaid_code):
    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinical Wisdom Map</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: false, theme: 'base' }});
        window.mermaid = mermaid;
    </script>
    <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
    
    <style>
        body {{ background-color: #f8fafc; height: 100vh; overflow: hidden; }}
        #container {{ width: 100%; height: 100%; display: flex; flex-direction: column; }}
        #diagram-wrapper {{ flex-grow: 1; border: 1px solid #e2e8f0; background: white; overflow: hidden; position: relative; }}
        #mermaid-output {{ width: 100%; height: 100%; }}
        /* Ensure hidden pre tag is actually hidden */
        pre.mermaid-source {{ display: none; }}
        .controls {{ position: absolute; bottom: 20px; right: 20px; z-index: 10; display: flex; gap: 10px; }}
    </style>
</head>
<body>
    <div id="container">
        <header class="bg-white shadow-sm p-4 z-10">
            <h1 class="text-xl font-bold text-slate-800">Grand Rounds: Clinical Reasoning Map</h1>
            <p class="text-sm text-slate-500">Visualizing the evolution of medical consensus.</p>
        </header>

        <div id="diagram-wrapper">
            <div class="controls">
                <button onclick="resetZoom()" class="bg-slate-800 text-white px-4 py-2 rounded shadow hover:bg-slate-700 transition">Reset View</button>
            </div>
            
            <!-- Hidden source block -->
            <pre class="mermaid-source" id="graph-definition">
{mermaid_code}
            </pre>
            
            <div id="mermaid-output"></div>
        </div>
    </div>

    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        
        async function renderDiagram() {{
            const sourceElement = document.querySelector('#graph-definition');
            const outputElement = document.querySelector('#mermaid-output');
            const graphDefinition = sourceElement.textContent;
            
            try {{
                // Render the graph
                const {{ svg }} = await mermaid.render('rendered-svg', graphDefinition);
                outputElement.innerHTML = svg;
                
                // Initialize Pan/Zoom on the new SVG
                const svgElement = outputElement.querySelector('svg');
                svgElement.setAttribute('width', '100%');
                svgElement.setAttribute('height', '100%');
                
                window.panZoomInstance = svgPanZoom(svgElement, {{
                    zoomEnabled: true,
                    controlIconsEnabled: false,
                    fit: true,
                    center: true,
                    minZoom: 0.5,
                    maxZoom: 10
                }});
            }} catch (e) {{
                outputElement.innerHTML = `<div style="color:red; padding:20px">Error rendering diagram: ${{e.message}}</div>`;
                console.error(e);
            }}
        }}

        renderDiagram();
    </script>

    <script>
        function resetZoom() {{
            if (window.panZoomInstance) {{
                window.panZoomInstance.reset();
                window.panZoomInstance.fit();
                window.panZoomInstance.center();
            }}
        }}
    </script>
</body>
</html>
    """
    return html_template

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    transcript_file = 'requested_transcript.en.srt' 
    
    print(f"Reading {transcript_file}...")
    transcript_text = parse_srt(transcript_file)
    
    if transcript_text:
        print("Analyzing transcript and mapping logic...")
        mermaid_def = generate_reasoning_map(transcript_text)

        if mermaid_def:
            print("Generating Interactive UI...")
            full_html = create_interactive_html(mermaid_def)
            
            with open('reasoning_map.html', 'w', encoding='utf-8') as f:
                f.write(full_html)
            
            # ALSO update index.html for the integrated view
            try:
                with open('index.html', 'r') as f:
                    index_html = f.read()
                
                # Update the hidden pre tag content
                pattern = re.compile(r'(<pre class="mermaid-source" id="graph-definition">)(.*?)(</pre>)', re.DOTALL)
                # Note: index.html might have slightly different ID or structure from previous manual edits.
                # We should be careful. The previous turn used 'id="graph-definition"' inside reasoning_map.html
                # but index.html might be using 'id="mermaid-source"'.
                # Let's try to target the specific block we added earlier.
                
                # If the user is using the dashboard (index.html), we need to ensure it has the structure to support this.
                # Let's check if we need to rewrite the index.html graph section specifically.
                
                # We'll try to replace the content of the pre tag we injected last time.
                # The last write to index.html used: <pre class="mermaid-source" id="graph-definition">
                # Wait, the previous index.html write used: <pre id="mermaid-source"> (and then we updated reasoning_map.html to use class="mermaid-source" id="graph-definition")
                # Let's try to match the ID 'mermaid-source' which is what index.html likely has.
                
                pattern_index = re.compile(r'(<pre id="mermaid-source">)(.*?)(</pre>)', re.DOTALL)
                
                if pattern_index.search(index_html):
                    new_index_html = pattern_index.sub(r'\1\n' + mermaid_def + r'\n\3', index_html)
                    with open('index.html', 'w') as f:
                        f.write(new_index_html)
                    print("Map also updated in main dashboard (index.html)")
                else:
                    # If that fails, try the ID used in reasoning_map logic just in case they were synced
                    pattern_alt = re.compile(r'(<pre class="mermaid-source" id="graph-definition">)(.*?)(</pre>)', re.DOTALL)
                    if pattern_alt.search(index_html):
                        new_index_html = pattern_alt.sub(r'\1\n' + mermaid_def + r'\n\3', index_html)
                        with open('index.html', 'w') as f:
                            f.write(new_index_html)
                        print("Map updated in index.html (alt tag)")
                    else:
                        print("Could not find the map source container in index.html to update.")

            except Exception as e:
                print(f"Could not update index.html: {e}")
                
            print("Success! Open 'reasoning_map.html' for standalone view or 'index.html' for dashboard.")
        else:
            print("Failed to generate Mermaid definition.")
    else:
        print("Error: Could not read transcript file.")
