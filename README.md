# Grand Rounds Board Review: AI-Powered Medical Education

A Proof of Concept (POC) for an interactive, AI-enhanced medical education platform. This application transforms standard medical lectures (video + transcript) into an active learning experience featuring "Hot Seat" simulations, visual diagnostic maps, and Socratic AI tutoring.

## 🚀 Key Features

*   **🔥 "Hot Seat" Clinical Simulation**
    *   Pauses the lecture at critical decision points.
    *   Challenges the learner to commit to a diagnosis or next step.
    *   Provides instant, AI-graded Socratic feedback comparing the learner's logic to the expert's.

*   **🗺️ Visual Differential Map**
    *   Dynamically generates a "Wisdom Topology" (Mermaid.js graph) of the clinical reasoning flow.
    *   Visualizes the shift from presentation → differential debate → final diagnosis.

*   **🤖 Contextual AI Chat**
    *   RAG (Retrieval-Augmented Generation) chatbot acting as the speaker.
    *   Answers questions strictly based on the transcript, citing specific timestamps `[T=123]`.

*   **📝 Board-Style Quiz**
    *   Auto-generated high-yield questions focusing on clinical nuance and "great mimickers."

## 🛠️ Architecture

*   **Backend**: Python (`http.server` extended) handling API requests for Chat and Grading.
*   **Frontend**: Vanilla HTML/JS/CSS (No build step required).
*   **AI Engine**: Google Gemini 2.5 Pro (via `google-generativeai`).
*   **Data**: JSON-based content generated from SRT transcripts.

## 📦 Project Structure

```text
├── server.py              # Main application server (Port 8000)
├── public/                # Frontend static assets
│   ├── index.html         # Main dashboard
│   └── visual_map.html    # Standalone visual map
├── data/                  # Data persistence
│   ├── quiz_data.json     # Generated quiz content
│   ├── simulation_data.json # Generated Hot Seat scenarios
│   └── requested_transcript.en.srt # Source transcript
├── scripts/               # Content generation pipelines
│   ├── generate_quiz.py
│   ├── generate_hot_seat.py
│   ├── generate_visual_map.py
│   └── utils.py           # Shared utilities (SRT parsing)
└── tests/                 # Comprehensive test suite
```

## ⚡ Quick Start

### 1. Prerequisites
*   Python 3.10+
*   A Google AI Studio API Key (for Gemini)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/gocarob/carob-case-poc.git
cd carob-case-poc

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the root directory:

```ini
GOOGLE_API_KEY=your_gemini_api_key_here
# Optional: Azure keys if running extraction scripts
```

### 4. Running the Application

```bash
# Start the server
python server.py
```
Open **http://localhost:8000** in your browser.

## 🔄 Content Generation Workflow

To generate new interactive content from a raw transcript (`data/requested_transcript.en.srt`):

```bash
# Generate the Quiz JSON
python scripts/generate_quiz.py

# Generate the Hot Seat Simulation JSON
python scripts/generate_hot_seat.py

# Generate the Visual Reasoning Map (HTML/Mermaid)
python scripts/generate_visual_map.py
```

## 🧪 Testing

The project includes a comprehensive test suite covering content integrity, API endpoints, and end-to-end functionality.

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test module
python -m unittest tests/test_e2e.py
```

## 📝 License
Private Repository - Carob Health / GoCarob.

