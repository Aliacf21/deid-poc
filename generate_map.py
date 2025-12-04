import google.generativeai as genai

def generate_wisdom_graph(full_transcript_text):
    # Using Gemini 1.5 Pro for its ability to analyze nuance and sentiment
    model = genai.GenerativeModel('gemini-1.5-pro')

    prompt = f"""
### ROLE
You are a Medical Decision-Making Analyst and Cognitive Ethnographer.
Your goal is not just to map the diagnosis, but to map the **"Wisdom of the Crowd"**—the specific cognitive processes, debates, and experience-based pattern matching used by the medical team to navigate uncertainty.

### INPUT TRANSCRIPT
{full_transcript_text}

### OBJECTIVE
Create a Mermaid.js flowchart that visualizes the **Evolution of Consensus**.
Dr. Harvey Rubin defines "Wisdom" in this context as the intersection of **Uncertainty**, **Collective Experience**, and **Decision Making**. Your chart must highlight these elements.

### MERMAID ARCHITECTURE
**Orientation:** `graph TD`

**Strictly use these 4 Subgraphs to represent the "Wisdom Loop":**

1.  `subgraph The_Facts [The "Known Knowns"]`
    * Include the "Textbook" data presented: Age, Origin, Vitals, Labs.
    * *Source:* "51 year old man from Honduras... fever and chills" (Rubin, 17:50).

2.  `subgraph The_Deliberation [The "Informal Economy"]`
    * **CRITICAL:** This is where "Wisdom" lives. You must visualize the *divergence* of opinion.
    * If a Fellow suggests X and a Senior Faculty suggests Y, visualize both branches.
    * **Pattern Recognition Nodes:** If a speaker references past experience ("I saw a case like this..."), create a specific node shape for this.
    * **Uncertainty Edges:** Label connecting lines with confidence levels if detectable (e.g., `-->|High Confidence|` or `-.->|Low Certainty|`).

3.  `subgraph The_Consensus [The Wise Decision]`
    * Show how the group converged on a recommendation.
    * Was it a compromise? A test of exclusion? A "wait and see"?

4.  `subgraph The_Outcome [The Feedback Loop]`
    * Did the patient improve or "crump"?
    * Connect this back to the Consensus node to show the validation of the wisdom.

### VISUAL STYLING RULES (Apply `class` at the end)
* **Fact Nodes:** `classDef fact fill:#e3f2fd,stroke:#1565c0,shape:rect;` (Standard Blue)
* **Experience Nodes (Wisdom):** `classDef wisdom fill:#fff9c4,stroke:#fbc02d,stroke-width:3px,shape:hexagon;` (Yellow Hexagon)
    * *Usage:* Use this for nodes where a doctor cites personal experience/pattern matching.
* **Uncertainty/Debate Nodes:** `classDef debate fill:#f3e5f5,stroke:#8e24aa,stroke-dasharray: 5 5;` (Purple Dashed)
* **Action/Consensus:** `classDef action fill:#c8e6c9,stroke:#2e7d32,stroke-width:4px;` (Green)

### LOGIC INSTRUCTIONS
1.  **Identify the "Pivot":** Look for the moment the "Textbook" answer was rejected for the "Wise" answer.
2.  **Cite Experience:** If the transcript contains a phrase like "I recall a patient...", that MUST be a `wisdom` class node.
3.  **Map the Uncertainty:** If the team is unsure, use a dotted line `-.->` labeled "Uncertain".

### OUTPUT FORMAT
Return **ONLY** the raw Mermaid definition text. Start directly with `graph TD`.
"""

    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace('```mermaid', '').replace('```', '').strip()
        return clean_text
    except Exception as e:
        print(f"Error generating map: {e}")
        return None