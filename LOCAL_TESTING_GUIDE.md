# Local Model Testing Guide

This guide explains how to test The Truth Machine using local models instead of OpenAI's API. This allows you to run fact-checking tests without API costs and with complete control over the model.

## 🎯 Overview

The local testing system replaces OpenAI API calls with local model calls while keeping all other functionality:
- ✅ Google Custom Search (for finding Wikipedia articles)
- ✅ Wikipedia content scraping
- ✅ Local model fact-checking
- ✅ Complete test pipeline with accuracy scoring

## 📋 Prerequisites

### Required Software
1. **Python 3.8+** - [Download here](https://www.python.org/downloads/)
2. **LM Studio** - [Download here](https://lmstudio.ai/) (recommended)
   - Alternative: Ollama, or any OpenAI-compatible local server
3. **Google Custom Search API** - [Get API key here](https://developers.google.com/custom-search/v1/introduction)

### Required Python Packages

**Windows:**
```bash
py -m pip install requests pydantic pydantic-settings python-dotenv beautifulsoup4
```

**macOS/Linux:**
```bash
python3 -m pip install requests pydantic pydantic-settings python-dotenv beautifulsoup4
```

## 🚀 Quick Start

### 1. Set Up Environment Variables

Create a `.env` file in the project root:

```env
CUSTOM_SEARCH_API_KEY=your_google_api_key_here
CUSTOM_SEARCH_ENGINE_ID=your_google_engine_id_here
```

**Note:** No OpenAI API key needed for local testing!

### 2. Set Up Local Model

#### Option A: LM Studio (Recommended)
1. Download and install [LM Studio](https://lmstudio.ai/)
2. Open LM Studio
3. Go to "Models" tab → Download a model (e.g., "Llama 3.1 8B Instruct")
4. Go to "Local Server" tab → Click "Start Server"
5. Note the URL (usually `http://localhost:1234`)

#### Option B: Ollama
1. Install [Ollama](https://ollama.ai/)
2. Run: `ollama pull llama2`
3. Run: `ollama serve`
4. Server runs on `http://localhost:11434`

### 3. Test the System

**Windows:**
```bash
# Test with 5 cases (quick test)
py src/test_full_local_system.py --max-tests 5

# Test with all cases
py src/test_full_local_system.py

# Test with specific model
py src/test_full_local_system.py --model "llama-3.1-8b-instruct"
```

## 📊 Available Test Datasets

The system includes 5 different test datasets:

### 1. Wikipedia Dataset (Default)
```bash
py src/test_full_local_system.py --dataset test_claims_wikipedia
```
- **50 test cases** with Wikipedia-sourced claims
- Mix of True/False claims about history, science, geography
- **Example:** "Lebanon gained its independence in 1943" (True)

### 2. Reasoning Dataset
```bash
py src/test_full_local_system.py --dataset test_claims_reasoning
```
- **Complex reasoning** claims requiring logical thinking
- **Example:** "The iPhone was released after the first Android phone" (False)

### 3. Conflicts Dataset
```bash
py src/test_full_local_system.py --dataset test_claims_conflicts
```
- **Conflicting information** that requires up-to-date knowledge
- **Example:** "Pluto is officially classified as a planet" (False)

### 4. Language Variation Dataset
```bash
py src/test_full_local_system.py --dataset test_claims_language_variation
```
- **Casual language** and informal expressions
- **Example:** "Einstein came up with relativity, right?" (True)

### 5. Retrieval Stress Dataset
```bash
py src/test_full_local_system.py --dataset test_claims_retrieval_stress
```
- **Challenging retrieval** scenarios
- Tests model's ability to find relevant information

## 🔧 Command Line Options

### Basic Usage
```bash
py src/test_full_local_system.py [OPTIONS]
```

### Available Options
- `--max-tests N` - Test only first N cases (default: all)
- `--dataset NAME` - Choose dataset (default: test_claims_wikipedia)
- `--base-url URL` - Local model server URL (default: http://localhost:1234)
- `--model NAME` - Model name (default: local-model)
- `--output FILE` - Save results to JSON file

### Examples
```bash
# Quick test with 5 cases
py src/test_full_local_system.py --max-tests 5

# Test reasoning dataset with specific model
py src/test_full_local_system.py --dataset test_claims_reasoning --model "llama-3.1-8b-instruct"

# Test conflicts dataset and save results
py src/test_full_local_system.py --dataset test_claims_conflicts --output results.json

# Test with Ollama
py src/test_full_local_system.py --base-url http://localhost:11434 --model llama2
```

## 📈 Understanding Results

### Sample Output
```
============================================================
FULL LOCAL SYSTEM TEST RESULTS
============================================================
Total Tests: 50
Correct: 42
Accuracy: 84.00%
Errors: 2
Average Processing Time: 3.45s

Per-Label Accuracy:
True Claims: 25/25 (100.00%)
False Claims: 17/25 (68.00%)

Detailed Results:
ID   Expected Predicted  Correct  Time     Error
----------------------------------------------------------------------
1    True     True       True     3.21s    
2    False    True       False    2.98s    
...
```

### Scoring System
- **Correct Prediction:** 1/1 score
- **Incorrect Prediction:** 0/1 score
- **Total Score:** Sum of all individual scores
- **Accuracy:** Percentage of correct predictions

## 🎯 Recommended Models

### For Best Performance
1. **Llama 3.1 8B Instruct** - Excellent balance of speed and accuracy
2. **Llama 3.1 70B** - Highest accuracy (requires powerful hardware)
3. **Qwen2.5 72B** - Great reasoning capabilities

### For Testing
1. **Llama 2 7B** - Good baseline performance
2. **Mixtral 8x7B** - Fast inference

## 🔧 Troubleshooting

### Common Issues

#### 1. "Module not found" errors
```bash
py -m pip install requests pydantic pydantic-settings python-dotenv beautifulsoup4
```

#### 2. "Connection failed" to local model
- Ensure LM Studio server is running
- Check the base URL and port
- Verify model is loaded

#### 3. "400 Bad Request" errors
- Model context window too small
- Try a model with larger context (Llama 3.1 8B+)
- The system automatically handles content truncation

#### 4. "API key" errors
- Check your `.env` file format (no spaces around `=`)
- Ensure Google Custom Search API key is valid

### Environment File Format
**Correct:**
```env
CUSTOM_SEARCH_API_KEY=your_key_here
CUSTOM_SEARCH_ENGINE_ID=your_id_here
```

**Incorrect:**
```env
CUSTOM_SEARCH_API_KEY = your_key_here  # ❌ Spaces around =
```

## 🚀 Advanced Usage

### Run Multiple Datasets
```bash
# Test all datasets
for dataset in test_claims_wikipedia test_claims_reasoning test_claims_conflicts test_claims_language_variation test_claims_retrieval_stress; do
  py src/test_full_local_system.py --dataset $dataset --output "results_$dataset.json"
done
```

### Compare Models
```bash
# Test with different models
py src/test_full_local_system.py --model "llama-3.1-8b-instruct" --output results_llama3.1.json
py src/test_full_local_system.py --model "llama2" --output results_llama2.json
```

### Custom Queries
```bash
# Test specific claims
py src/main_local.py "The Eiffel Tower is in Paris"
py src/main_local.py "Water boils at 100 degrees Celsius"
```

## 📊 Expected Performance

### Typical Accuracy Ranges - TBD
- **Llama 3.1 8B:** 75-85%
- **Llama 3.1 70B:** 85-95%
- **GPT-OSS-20B:** 60-75%

### Performance Factors
- **Model size** - Larger models generally perform better
- **Context window** - Larger context = better fact-checking
- **Dataset type** - Some datasets are more challenging than others

## 🎉 Success!

Once everything is working, you'll have:
- ✅ **Complete local fact-checking system**
- ✅ **No API costs** for testing
- ✅ **Full control** over the model
- ✅ **Comprehensive testing** across multiple datasets
- ✅ **Detailed accuracy metrics**

## 📝 Next Steps

1. **Test different models** to find the best performance
2. **Run all datasets** to understand model capabilities
3. **Save results** for comparison and analysis
4. **Experiment with prompts** by modifying the local client
5. **Scale up** to test with larger datasets

## 🤝 Contributing

To add support for new local model providers:
1. Modify `src/utils/local_openai_client.py`
2. Add new provider support
3. Update this guide

## 📄 License

This local testing system is part of The Truth Machine project and follows the same license terms.
