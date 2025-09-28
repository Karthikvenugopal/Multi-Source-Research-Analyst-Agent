# 🆓 Free Setup Guide - Multi-Source Research Analyst Agent

## 🎯 Completely Free Options

You can run this project **completely free** using open-source models! Here are your options:

## Option 1: 🤗 HuggingFace (Recommended - No API Key Required)

This is the **easiest and completely free** option:

### Setup Steps:

1. **Install dependencies**:

   ```bash
   pip install langchain-huggingface transformers torch
   ```

2. **Create .env file**:

   ```env
   # HuggingFace (FREE - No API key needed)
   LLM_PROVIDER=huggingface
   LLM_MODEL=microsoft/DialoGPT-medium

   # Tavily API (FREE - Get key at https://tavily.com)
   TAVILY_API_KEY=your_tavily_key_here
   ```

3. **Run the project**:
   ```bash
   python app.py
   ```

### Free HuggingFace Models Available:

- `microsoft/DialoGPT-medium` (Recommended)
- `facebook/blenderbot-400M-distill`
- `microsoft/DialoGPT-small`
- `facebook/blenderbot-90M`

## Option 2: 🔍 Google Gemini (Free with API Key)

Get a **free API key** from Google:

### Setup Steps:

1. **Get free API key**:

   - Visit: https://makersuite.google.com/app/apikey
   - Sign up for free
   - Create an API key

2. **Install dependencies**:

   ```bash
   pip install langchain-google-genai
   ```

3. **Create .env file**:

   ```env
   # Google Gemini (FREE with API key)
   LLM_PROVIDER=google
   LLM_MODEL=gemini-1.5-flash
   GOOGLE_API_KEY=your_google_key_here

   # Tavily API (FREE)
   TAVILY_API_KEY=your_tavily_key_here
   ```

4. **Run the project**:
   ```bash
   python app.py
   ```

## Option 3: 🤖 OpenAI (Paid)

If you want to use OpenAI (requires payment):

```env
# OpenAI (PAID)
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=your_openai_key_here

# Tavily API (FREE)
TAVILY_API_KEY=your_tavily_key_here
```

## 🚀 Quick Start (Free)

### Step 1: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For HuggingFace (free option)
pip install langchain-huggingface transformers torch
```

### Step 2: Get Free API Keys

1. **Tavily API** (for web search):

   - Visit: https://tavily.com
   - Sign up for free
   - Get your API key

2. **HuggingFace** (for LLM):
   - No API key needed! 🎉

### Step 3: Configure Environment

Create `.env` file:

```env
# LLM Configuration (FREE)
LLM_PROVIDER=huggingface
LLM_MODEL=microsoft/DialoGPT-medium

# Web Search API (FREE)
TAVILY_API_KEY=your_tavily_key_here
```

### Step 4: Run the Project

```bash
python app.py
```

## 📊 Free vs Paid Comparison

| Feature     | HuggingFace (Free)   | Google Gemini (Free) | OpenAI (Paid)        |
| ----------- | -------------------- | -------------------- | -------------------- |
| **Cost**    | 🆓 Completely Free   | 🆓 Free with API key | 💰 Paid              |
| **API Key** | ❌ Not required      | ✅ Required          | ✅ Required          |
| **Quality** | ⭐⭐⭐ Good          | ⭐⭐⭐⭐ Very Good   | ⭐⭐⭐⭐⭐ Excellent |
| **Speed**   | ⭐⭐ Moderate        | ⭐⭐⭐⭐ Fast        | ⭐⭐⭐⭐⭐ Very Fast |
| **Setup**   | ⭐⭐⭐⭐⭐ Very Easy | ⭐⭐⭐⭐ Easy        | ⭐⭐⭐ Moderate      |

## 🎯 Recommended Free Setup

For the **best free experience**, I recommend:

1. **HuggingFace** for the LLM (no API key needed)
2. **Tavily** for web search (free API key)
3. **Wikipedia & ArXiv** (no API keys needed)

This gives you a **completely free** research agent with:

- ✅ No monthly costs
- ✅ No API key requirements for LLM
- ✅ High-quality research capabilities
- ✅ Professional reports

## 🔧 Troubleshooting

### HuggingFace Issues:

```bash
# If you get CUDA errors, install CPU version:
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Memory Issues:

```bash
# Use smaller model:
LLM_MODEL=facebook/blenderbot-90M
```

### Google Gemini Issues:

- Make sure you have a valid API key
- Check your Google Cloud billing (should be free tier)

## 🎉 Success!

Once set up, you'll have a **completely free** research agent that can:

- 🔍 Research any topic
- 📚 Use multiple sources
- 🧠 Synthesize information
- 📊 Generate quality reports
- 💰 Cost you nothing!

Enjoy your free AI research assistant! 🚀
