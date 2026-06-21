# 🤖 Multi-Source Research Analyst Agent

An intelligent AI agent that autonomously researches topics using multiple sources and synthesizes comprehensive reports with citations and confidence scores.

## 🌟 Features

- **🔄 Autonomous Decision-Making**: The agent intelligently decides which sources to use and when to stop researching
- **📚 Multi-Source Research**: Gathers information from web search, Wikipedia, and academic papers (ArXiv)
- **🧠 Intelligent Synthesis**: Handles conflicting information and provides balanced analysis
- **📊 Quality Metrics**: Tracks research quality, confidence scores, and source diversity
- **📝 Professional Reports**: Generates well-structured reports with proper citations
- **🎯 Real-time Interface**: Beautiful Gradio interface with progress tracking

## 📊 Evaluation (model-graded)

Report quality is measured by an **LLM-as-judge** (`evals/judge.py`): a separate
Gemini model grades each generated report against the evidence the agent actually
retrieved, on three axes in `[0, 1]` — replacing guesswork with measurable scores.

- **Faithfulness** — are the report's claims grounded in the retrieved evidence (not hallucinated)?
- **Answer relevance** — does the report actually answer the question?
- **Citation coverage** — are substantive claims attributed to a source?

Reproduce with `python -m evals.run_eval` (questions in `datasets/eval_questions.jsonl`).

_Agent: `gemini-2.5-flash-lite` · Judge: `gemini-2.5-flash` (temperature 0) · 3 questions._
_(Eval runs the agent on the cheaper flash-lite to stay within free-tier limits; the default agent model is `gemini-2.5-flash`.)_

| Question | Faithfulness | Relevance | Citations | Overall |
| --- | :---: | :---: | :---: | :---: |
| Factual — *what is RAG?* | 1.00 | 0.95 | 0.90 | **0.95** |
| Technical — *transformers & self-attention* | 0.30 | 0.10 | 0.50 | **0.30** |
| Comparative — *solar vs. wind energy* | 1.00 | 0.90 | 1.00 | **0.97** |
| **Mean** | **0.77** | **0.65** | **0.80** | **0.74** |

**What the eval surfaced:** the technical question scored poorly because the agent
currently sends the *full natural-language question* as the search query to every
source; for long questions this returns weak Wikipedia/ArXiv hits, so the report
can't ground its answer. Per-source **query reformulation** is the next, eval-driven
improvement.

## 🏗️ Architecture

The agent is built using **LangGraph**, a framework for building stateful, multi-actor applications with LLMs. The architecture follows a cyclic "Reason → Act → Observe" pattern:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Supervisor    │───▶│  Research Node  │───▶│   Synthesis     │
│   (Decision)    │    │  (Information)   │    │   (Analysis)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                       │                       │
         │                       ▼                       ▼
         │              ┌─────────────────┐    ┌─────────────────┐
         └───────────────│   Web Search    │    │   Final Report │
                         │   Wikipedia     │    │   Generation    │
                         │   ArXiv         │    └─────────────────┘
                         └─────────────────┘
```

### Core Components

1. **State Management** (`state.py`): Tracks research progress, findings, and quality metrics
2. **Research Tools** (`tools.py`): Interfaces with external APIs (Tavily, Wikipedia, ArXiv)
3. **Agent Nodes** (`nodes.py`): Core logic for decision-making, research, and synthesis
4. **Graph Orchestration** (`graph.py`): Manages the flow between nodes
5. **User Interface** (`app.py`): Gradio-based web interface

## 🚀 Quick Start

### 🆓 FREE Options Available!

You can run this project **completely free** using open-source models! No paid API keys required.

### Prerequisites

- Python 3.8+
- Tavily API key (free at https://tavily.com)
- **Optional**: OpenAI API key (paid) or Google API key (free)

### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd Multi-Source-Research-Analyst-Agent
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Choose your LLM provider**:

   **🆓 Option 1: HuggingFace (Completely Free - No API Key)**

   ```env
   LLM_PROVIDER=huggingface
   LLM_MODEL=microsoft/DialoGPT-medium
   TAVILY_API_KEY=your_tavily_key_here
   ```

   **🆓 Option 2: Google Gemini (Free with API Key)**

   ```env
   LLM_PROVIDER=google
   LLM_MODEL=gemini-1.5-flash
   GOOGLE_API_KEY=your_google_key_here
   TAVILY_API_KEY=your_tavily_key_here
   ```

   **💰 Option 3: OpenAI (Paid)**

   ```env
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-3.5-turbo
   OPENAI_API_KEY=your_openai_key_here
   TAVILY_API_KEY=your_tavily_key_here
   ```

### Running the Agent

1. **Start the web interface**:

   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to `http://localhost:7860`

3. **Enter a research question** and watch the agent work!

### 🆓 Free Setup Guide

For detailed instructions on setting up the **completely free** version, see:

- **[FREE_SETUP.md](FREE_SETUP.md)** - Complete free setup guide
- **HuggingFace models** (no API key required)
- **Google Gemini** (free with API key)

### Running Tests

```bash
python test_agent.py
```

## 📊 How It Works

### 1. Research Process

The agent follows an iterative research process:

1. **Supervisor Decision**: Analyzes current state and decides next action
2. **Information Gathering**: Uses appropriate tools based on decision
3. **Quality Assessment**: Evaluates research quality and source diversity
4. **Synthesis**: Combines findings into coherent analysis
5. **Report Generation**: Creates professional report with citations

### 2. Decision Logic

The supervisor makes decisions based on:

- **Research Quality Score**: Overall confidence in findings
- **Source Diversity**: Number of different source types used
- **Iteration Count**: Prevents infinite loops
- **Question Complexity**: Adapts strategy to question type

### 3. Quality Metrics

- **Confidence Scores**: Each finding has a 0-1 confidence score
- **Source Reliability**: Different weights for different source types
- **Diversity Bonus**: Rewards using multiple source types
- **Quality Penalties**: Reduces score for low-quality findings

## 🔧 Configuration

### Model Settings

Edit `config.py` to customize:

```python
class Config:
    LLM_MODEL = "gpt-3.5-turbo"  # or "gpt-4"
    MAX_ITERATIONS = 5  # Maximum research cycles
```

### API Keys

- **OpenAI**: Required for LLM calls
- **Tavily**: Required for web search (get free key at tavily.com)
- **Wikipedia/ArXiv**: No API keys required

## 📈 Performance Metrics

The agent tracks several performance metrics:

- **Duration**: Total research time
- **Quality Score**: Overall research quality (0-1)
- **Iterations**: Number of research cycles
- **Source Diversity**: Number of different sources used
- **Confidence**: Average confidence in findings

## 🧪 Testing

The included test suite evaluates the agent with various research questions:

```bash
python test_agent.py
```

Test cases include:

- Basic factual questions
- Current events research
- Comparative analysis
- Technical/scientific topics
- Complex multi-faceted questions

## 🎯 Example Research Questions

Try these example questions to see the agent in action:

- "What are the latest developments in quantum computing?"
- "Compare renewable energy policies in Germany and Japan"
- "What are the competing theories about dark matter?"
- "How does climate change affect global food security?"
- "What are the economic implications of AI automation?"

## 🔍 Advanced Features

### Custom Research Focus

The agent can focus on specific aspects of a question:

```python
# The agent will adapt its research strategy based on the question type
question = "What are the health effects of intermittent fasting?"
# Agent will prioritize scientific sources and recent studies
```

### Quality Control

Built-in safeguards prevent:

- Infinite research loops
- Low-quality source over-reliance
- Information bias
- Hallucination

### Source Attribution

Every finding includes:

- Source type and reliability score
- URL (when available)
- Timestamp
- Confidence level

## 🛠️ Development

### Project Structure

```
Multi-Source-Research-Analyst-Agent/
├── app.py              # Gradio web interface
├── graph.py            # LangGraph orchestration
├── nodes.py            # Agent logic and prompts
├── state.py            # State management
├── tools.py            # External API integrations
├── config.py           # Configuration settings
├── test_agent.py       # Test suite
├── requirements.txt    # Dependencies
└── README.md           # This file
```

### Adding New Sources

To add a new research source:

1. **Add tool method** in `tools.py`:

   ```python
   def new_source_search(self, query: str) -> List[Dict[str, Any]]:
       # Implementation
   ```

2. **Add node** in `nodes.py`:

   ```python
   def new_source_node(self, state):
       # Implementation
   ```

3. **Update graph** in `graph.py`:
   ```python
   self.graph.add_node("new_source", self.nodes.new_source_node)
   ```

### Customizing Prompts

Edit prompts in `nodes.py` to customize:

- Supervisor decision logic
- Synthesis approach
- Report formatting
- Quality assessment criteria

## 📚 Dependencies

- **LangChain**: LLM framework and tools
- **LangGraph**: Stateful graph orchestration
- **Gradio**: Web interface
- **Tavily**: Web search API
- **Wikipedia**: Encyclopedia API
- **ArXiv**: Academic papers API

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain/LangGraph**: For the excellent agent framework
- **OpenAI**: For the powerful language models
- **Tavily**: For the web search capabilities
- **Wikipedia/ArXiv**: For the knowledge sources

## 🔮 Future Enhancements

- [ ] Additional research sources (news APIs, databases)
- [ ] Multi-language support
- [ ] Advanced fact-checking
- [ ] Research collaboration features
- [ ] Export to various formats (PDF, Word)
- [ ] Research history and bookmarking
- [ ] Custom research templates
- [ ] Integration with research databases

---

_Built with ❤️ using LangGraph and modern AI tools_
