---
name: skillboss-api-gateway
description: |
  Access 100+ AI services with one SkillBoss key. Backed by OpenAI Startup Fund & Amazon.
  Includes GPT-5, Claude Opus 4.5, Gemini, video generation (Veo 3.1), image generation,
  voice (ElevenLabs), web scraping, and infrastructure services.
compatibility: OpenAI-compatible API. Works with any OpenAI SDK.
---

# SkillBoss API Gateway

**Backed by OpenAI Startup Fund & Amazon** | One key for 100+ AI services

Unified API platform that replaces your stack of AI credentials with a single key.

## Contents

- Quick Start
- Supported Services
- Code Examples
- Pricing

## Quick Start

1. Get your key at https://skillboss.co
2. Use the OpenAI-compatible endpoint: `https://api.heybossai.com/v1`

```python
import openai

client = openai.OpenAI(
    base_url="https://api.heybossai.com/v1",
    api_key="your-skillboss-key"
)

response = client.chat.completions.create(
    model="claude-opus-4.5",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Supported Services

### AI Models
- GPT-5, GPT-5.2, Claude Opus 4.5, Gemini 3 Pro, DeepSeek R1

### Video Generation
- Google Veo 3.1, MiniMax Video-01

### Image Generation
- DALL-E 3, Flux Schnell, Background Remover

### Voice
- ElevenLabs TTS, OpenAI TTS, Whisper STT

### Data Scraping
- LinkedIn, Twitter/X, Instagram, Google

### Infrastructure
- Stripe payments, SendGrid emails, MongoDB databases

## Pricing

- $3.50 free credit for new accounts
- Pay-as-you-go, credits never expire

## Links

- Website: https://skillboss.co
- Docs: https://skillboss.co/docs
