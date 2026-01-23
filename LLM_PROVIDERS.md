# LLM Provider Configuration

The scraper automatically tries multiple LLM providers in order until one succeeds. Configure at least one provider by setting the appropriate environment variable.

## Supported Providers

### 1. Google Gemini (Recommended - Free Tier)
Free tier available with generous quota.

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

Get API key: https://makersuite.google.com/app/apikey

**Models tried:**
- gemini-2.0-flash-exp (8K tokens)
- gemini-1.5-flash-002 (8K tokens)
- gemini-1.5-flash (8K tokens)
- gemini-1.5-pro-002 (8K tokens)
- gemini-exp-1206 (8K tokens)

### 2. OpenRouter (Open-Source Models)
Access to many open-source models with free credits available.

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

Get API key: https://openrouter.ai/keys

**Models tried:**
- meta-llama/llama-3.1-405b-instruct (16K tokens)
- meta-llama/llama-3.1-70b-instruct (16K tokens)
- deepseek/deepseek-r1 (16K tokens)
- qwen/qwen-2.5-72b-instruct (16K tokens)
- microsoft/phi-3-medium-128k-instruct (16K tokens)

### 3. Hugging Face Inference API
Free tier available for many models.

```bash
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
```

Get API key: https://huggingface.co/settings/tokens

**Models tried:**
- meta-llama/Llama-3.1-70B-Instruct (8K tokens)
- Qwen/Qwen2.5-72B-Instruct (8K tokens)
- deepseek-ai/DeepSeek-R1 (8K tokens)

### 4. Anthropic Claude (Most Reliable - Paid)
Used as last resort for maximum reliability.

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Get API key: https://console.anthropic.com/

**Model:**
- claude-sonnet-4-20250514 (16K tokens)

## How It Works

1. **Automatic Detection**: The scraper detects which API keys are configured at initialization
2. **Sequential Fallback**: Tries models in order until one succeeds
3. **Smart Error Handling**: Automatically skips unavailable/quota-exceeded models
4. **No Configuration Required**: Just set environment variables and call the API

## Example .env File

```bash
# Recommended: Configure at least Gemini (free)
GEMINI_API_KEY=AIzaSy...

# Optional: Add more providers for redundancy
OPENROUTER_API_KEY=sk-or-v1-...
HUGGINGFACE_API_KEY=hf_...
ANTHROPIC_API_KEY=sk-ant-...
```

## API Usage

**Before (required llm_provider):**
```bash
curl -X POST http://localhost:5000/api/scraper/scrape \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "llm_provider": "gemini"}'
```

**After (automatic fallback):**
```bash
curl -X POST http://localhost:5000/api/scraper/scrape \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Troubleshooting

### "No LLM API keys configured" Error
**Solution**: Set at least one environment variable (GEMINI_API_KEY recommended)

### "All available LLM models failed" Error
**Causes:**
1. Quota exceeded on all configured providers
2. Network connectivity issues
3. Invalid API keys

**Solutions:**
- Check API key validity
- Verify quota/credits available
- Configure additional providers for redundancy
- Check network connectivity

### Model-Specific Errors
The scraper automatically skips problematic models and tries the next one. Check logs for details:
- `✓` indicates successful transformation
- `✗` indicates failed attempt with reason

## Free Tier Recommendations

For maximum reliability with free tiers:

1. **Primary**: Gemini (most generous free tier)
2. **Backup**: OpenRouter (free credits for testing)
3. **Fallback**: Hugging Face (free for small models)
4. **Last Resort**: Claude (paid but most reliable)

Configure all four for best results!
