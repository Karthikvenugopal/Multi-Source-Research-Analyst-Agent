# 🏗️ Multi-Source Research Analyst Agent Architecture

## System Overview

The Multi-Source Research Analyst Agent is built using **LangGraph**, a framework for building stateful, multi-actor applications with LLMs. The architecture follows a cyclic "Reason → Act → Observe" pattern that enables autonomous research capabilities.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESEARCH AGENT SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │   SUPERVISOR     │───▶│  RESEARCH NODES │───▶│   SYNTHESIS     │        │
│  │   (Decision)     │    │  (Information)  │    │   (Analysis)     │        │
│  │                 │    │                 │    │                 │        │
│  │ • Quality Check │    │ • Web Search    │    │ • Conflict      │        │
│  │ • Source Logic  │    │ • Wikipedia     │    │   Analysis      │        │
│  │ • Iteration     │    │ • ArXiv Papers  │    │ • Confidence    │        │
│  │   Control       │    │                 │    │   Scoring       │        │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘        │
│           ▲                       │                       │                │
│           │                       ▼                       ▼                │
│           │              ┌─────────────────┐    ┌─────────────────┐        │
│           └───────────────│   STATE         │    │   REPORT        │        │
│                           │   MANAGEMENT    │    │   GENERATION    │        │
│                           │                 │    │                 │        │
│                           │ • Findings      │    │ • Professional  │        │
│                           │ • Quality       │    │   Formatting    │        │
│                           │ • Sources       │    │ • Citations     │        │
│                           │ • Metrics       │    │ • Confidence    │        │
│                           └─────────────────┘    └─────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. State Management (`state.py`)

**Purpose**: Central state tracking for the entire research process

**Key Components**:

- `AgentState`: Main state object with research findings, quality metrics
- `ResearchFinding`: Individual finding with source, confidence, metadata
- State persistence across graph execution

**State Fields**:

```python
class AgentState(TypedDict):
    question: str                    # Research question
    research_findings: List[ResearchFinding]  # Accumulated findings
    analysis: str                   # LLM synthesis
    report: str                     # Final report
    iterations: int                 # Loop counter
    research_quality_score: float   # Overall quality (0-1)
    sources_used: List[str]         # Source diversity tracking
    max_iterations_reached: bool    # Safety flag
    start_time: str                 # Research start time
    current_focus: str              # Current research focus
```

### 2. Research Tools (`tools.py`)

**Purpose**: External API integrations for information gathering

**Tools**:

- **Web Search** (Tavily): Current news, recent developments
- **Wikipedia**: Established facts, historical context
- **ArXiv**: Academic papers, scientific research

**Features**:

- Error handling and fallback mechanisms
- Result formatting with metadata
- Confidence scoring
- Quality assessment

### 3. Agent Nodes (`nodes.py`)

**Purpose**: Core logic for decision-making, research, and synthesis

**Node Types**:

#### Supervisor Node

- **Input**: Current state with findings and metrics
- **Logic**: Quality-based decision making
- **Output**: Next action (web_search, wikipedia_search, arxiv_search, synthesize, finish)
- **Features**: Intelligent fallback, iteration control

#### Research Nodes

- **Web Search Node**: Current information gathering
- **Wikipedia Node**: Established facts and context
- **ArXiv Node**: Academic and scientific research

#### Synthesis Node

- **Input**: All accumulated findings
- **Process**: Conflict analysis, consensus identification
- **Output**: Coherent analysis with confidence scores

#### Report Node

- **Input**: Analysis and source information
- **Output**: Professional report with citations
- **Format**: Structured sections, proper attribution

### 4. Graph Orchestration (`graph.py`)

**Purpose**: Manages the flow between nodes using LangGraph

**Graph Structure**:

```
Entry Point: supervisor
    ↓
supervisor → [conditional routing] → research_nodes
    ↑                                    ↓
    └─────────── research_nodes ──────────┘
    ↓
synthesize → report → END
```

**Routing Logic**:

- Conditional edges based on supervisor decisions
- Loop back to supervisor after research
- Linear flow for synthesis and reporting

### 5. User Interface (`app.py`)

**Purpose**: Gradio-based web interface for user interaction

**Features**:

- Real-time progress tracking
- Enhanced report formatting
- Metrics display
- Error handling

## Data Flow

### 1. Initialization

```
User Question → Initial State → Supervisor Node
```

### 2. Research Loop

```
Supervisor → Research Node → State Update → Supervisor
     ↑                                           ↓
     └─── (Quality Check & Decision Logic) ──────┘
```

### 3. Synthesis

```
Sufficient Data → Synthesis Node → Analysis
```

### 4. Reporting

```
Analysis → Report Node → Final Report → User
```

## Quality Control Mechanisms

### 1. Iteration Limits

- Maximum iterations prevent infinite loops
- Configurable via `Config.MAX_ITERATIONS`

### 2. Quality Scoring

- Individual finding confidence (0-1)
- Source diversity bonus
- Quality penalty for low-confidence findings

### 3. Source Reliability

- **Wikipedia**: 0.9 confidence (established facts)
- **Web Search**: 0.8 confidence (current information)
- **ArXiv**: 0.85 confidence (academic sources)

### 4. Decision Logic

- Quality threshold checks
- Source diversity requirements
- Intelligent fallback mechanisms

## Performance Metrics

### Research Metrics

- **Duration**: Total research time
- **Quality Score**: Overall research quality (0-1)
- **Iterations**: Number of research cycles
- **Source Diversity**: Number of different sources used
- **Confidence**: Average confidence in findings

### Evaluation Criteria

- **Success Rate**: Percentage of successful research sessions
- **Quality Distribution**: Distribution of quality scores
- **Source Utilization**: Effectiveness of different sources
- **Error Rate**: Frequency of failures and errors

## Scalability Considerations

### Horizontal Scaling

- Stateless design allows multiple instances
- External API rate limiting considerations
- Database integration for research history

### Vertical Scaling

- Configurable model selection (GPT-3.5 vs GPT-4)
- Adjustable iteration limits
- Quality threshold tuning

## Security & Privacy

### API Key Management

- Environment variable configuration
- Secure key storage
- No hardcoded credentials

### Data Privacy

- No persistent storage of research data
- Temporary state only during execution
- User data not logged or stored

## Future Enhancements

### Planned Features

- Additional research sources
- Multi-language support
- Advanced fact-checking
- Research collaboration
- Export capabilities

### Technical Improvements

- Caching mechanisms
- Parallel research execution
- Advanced quality metrics
- Custom research templates

---

_This architecture enables sophisticated autonomous research capabilities while maintaining reliability, quality, and user experience._
