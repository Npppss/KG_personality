# Knowledge Graph & Personality Extraction Pipeline

Alternative global environment setup (Windows):
```bash
setx OPENAI_API_KEY "sk-<API_KEY_OPENAI>"
```

## Quick Start

**3 steps to get started immediately:**

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup API key:**
   Create a `.env` file with the following content:
   ```
   # Choose provider: openai or gemini
   LLM_PROVIDER=openai
   
   # OpenAI (if using OpenAI)
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   
   # Gemini (if using Gemini)
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-pro
   ```

3. **Run the pipeline:**
   ```bash
   python main.py --mode synthetic --n 3
   ```

4. **View results:**
   ```bash
   # Open the latest output folder
   cd outputs\runs
   dir /od
   
   # Open graph in browser (replace [timestamp] with the latest folder)
   start [timestamp]\graphs\doc0.html
   ```

---

## Installation and Setup

### 1. Environment Preparation
```bash
# Clone or download project
cd c:\Assigment

# Create virtual environment (optional but recommended)
python -m venv kg_personality
kg_personality\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. API Key Configuration
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
OUT_DIR=outputs
```

### 3. Installation Verification
```bash
# Test if all dependencies are installed
python -c "import openai, networkx, pyvis; print('Setup successful!')"
```

## How to Run

### Synthetic Mode (Recommended for Testing)
This mode uses LLM to generate synthetic data about scientists:

```bash
# Generate 3 synthetic documents
python main.py --mode synthetic --n 3

# Generate 5 synthetic documents
python main.py --mode synthetic --n 5
```

**Generated output:**
- Knowledge graphs for each document
- Personality extraction evaluation metrics
- Interactive HTML visualizations

### File Mode (For Real Data)
This mode processes existing text files:

```bash
# Prepare data folder with .txt files
mkdir data
# Put .txt files into data/ folder

# Run extraction
python main.py --mode file --input data/
```

### Result Visualization

#### 1. View Interactive Graph
```bash
# Open the latest output folder
cd outputs\runs\[latest-timestamp]

# Open HTML files in browser
start graphs\doc0.html
start graphs\doc1.html
```

#### 2. Generate Preview Graph (If HTML is Empty)
```bash
# Regenerate visualization with fallback
python preview_graph.py outputs\runs\[timestamp]\graphs\doc0.graphml

# Open result
start outputs\runs\[timestamp]\graphs\doc0.html
```

#### 3. Generate Analysis Report
```bash
# Create automatic report from run results
python report_builder.py outputs\runs\[timestamp]

# View report
start outputs\runs\[timestamp]\reports\report-*.md
```

## Output Structure

All results are saved in `OUT_DIR` (default: `outputs/`). Each run creates a subfolder with timestamp:

```
outputs/runs/20251022-083501/
├── graphs/
│   ├── doc0.graphml          # Graph in GraphML format
│   ├── doc0.html             # Interactive visualization
│   ├── doc1.graphml
│   └── doc1.html
├── sessions/
│   ├── session-kg-*.json     # Knowledge graph extraction logs
│   └── session-personality-*.json  # Personality extraction logs
├── reports/
│   └── report-*.md           # Automatic analysis reports
├── metrics.json              # Evaluation metrics (synthetic mode)
└── result.json               # Extraction results (file mode)
```

## Complete Example

**Run pipeline from start to finish:**

```bash
# 1. Install dependencies (including google-generativeai)
pip install -r requirements.txt

# 2. Setup API key (create .env file)
# For Gemini (default):
echo LLM_PROVIDER=gemini > .env
echo GEMINI_API_KEY=your-gemini-key >> .env

# Or for OpenAI:
echo LLM_PROVIDER=openai > .env
echo OPENAI_API_KEY=your-openai-key >> .env

# 3. Test with 1 document first
python main.py --mode synthetic --n 1

# 4. Check output
cd outputs\runs
dir /od
# A folder like this will appear: 20251022-093045

# 5. Open results
start 20251022-093045\graphs\doc0.html

# 6. View metrics
type 20251022-093045\metrics.json
```

**Expected output:**
- Folder `outputs\runs\[timestamp]\` contains:
  - `graphs\doc0.html` - Interactive visualization
  - `graphs\doc0.graphml` - Graph data
  - `metrics.json` - Personality evaluation
  - `sessions\` - LLM logs

## Troubleshooting

### Dependencies Error
```bash
# Install one by one if there are errors
pip install openai google-generativeai python-dotenv pydantic networkx pyvis orjson tqdm

# Test OpenAI
python -c "import openai; print('OpenAI OK!')"

# Test Gemini
python -c "import google.generativeai; print('Gemini OK!')"

# Test all
python -c "import openai, google.generativeai, networkx, pyvis; print('All OK!')"
```

### Provider Switching
```bash
# Switch to Gemini
echo LLM_PROVIDER=gemini > .env

# Switch to OpenAI
echo LLM_PROVIDER=openai > .env

# Test provider
python -c "from src.config import load_config; print('Provider:', load_config()['llm_provider'])"
```

### Empty HTML Graph
```bash
# Regenerate with fallback
python preview_graph.py outputs\runs\[timestamp]\graphs\doc0.graphml
```

### API Error
```bash
# Test with 1 document first
python main.py --mode synthetic --n 1

# Check API key in .env
type .env
```

## Data Schema

Entities:
- `Person`, `Organization`, `Event`, `Location`, `Concept`.

Relations (canonical):
- General: `WORKS_AT`, `ATTENDED`, `FRIEND_OF`, `LOCATED_IN`, `CAUSES`, `MENTIONS`, `LEADS`, `MANAGES`, `FOUNDED`, `COLLABORATES_WITH`.
- Scientific: `AFFILIATED_WITH`, `PUBLISHED_IN`, `AUTHORED`, `DISCOVERED`, `INVENTED`, `ADVISED`, `AWARDED`, `RESEARCHES`.

Personality:
- Big Five (OCEAN) with float values `[0,1]` in `Person` nodes.

## LLM Prompt Chain
- KG Extraction: per paragraph; results `entities`/`relations` plus evidence/confidence.
- Personality Inference: for all `Person`; OCEAN scores + brief justification.
- Synthetic Data: 3-paragraph narrative + ground-truth + personality scores.
- Report: ask LLM to write final report (approach, data, evaluation, limitations).

## Evaluation
- Entities: precision/recall/F1 over `(name, type)`.
- Relations: precision/recall/F1 over `(source, type, target)`.
- Personality: MAE/MSE against synthetic ground-truth.
- Graph diagnostics: degree, components, type ratios.

## Customization
- Prompts: `src/prompts.py`. For scientists, `SYNTHETIC_DATA_SYSTEM` directs affiliations, venues, awards, etc.
- Relation normalization: edit `src/normalization.py` (`RELATION_CANON`) to map synonyms to canonical labels.
- Visualization: modify `preview_graph.py` for colors, tooltips, legends.

## Troubleshooting
- `ImportError` relative imports — use `from src...` in `main.py`.
- `401 Incorrect API key` — ensure `.env` is correct and `OpenAI(api_key=...)` is used in `LLMClient`.
- pyvis/jinja error — upgrade/reinstall, or use fallback HTML in `preview_graph.py`.
- Inconsistent personality JSON format — parser in `main.py` already converts list to dict when possible; prompt also tightened.

## Sharing LLM Sessions
- Use LLM's "Share" feature, or attach `outputs\runs\<timestamp>\sessions\session-*.json` in submission.

## Future Plans
- RDF/JSON-LD export; Neo4j integration.
- Stronger coreference, dedup, canonicalization.
- Better evidence tracking and confidence calibration.
