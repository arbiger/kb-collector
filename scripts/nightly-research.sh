#!/bin/bash
# KB Collector - Nightly Research
# Usage: ./nightly-research.sh [--save] [--send]
# Uses Tavily API for searching AI/LLM/tech trends

# Load configuration from .env if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "$PARENT_DIR/.env" ]; then
    export $(grep -v '^#' "$PARENT_DIR/.env" | xargs)
fi

VAULT="${VAULT_PATH:-~/Documents/Knowledge}"
# Expand tilde if present
VAULT="${VAULT/#\~/$HOME}"

RECIPIENT="${RECIPIENT_EMAIL:-your-email@example.com}"
TAVILY_KEY="${TAVILY_API_KEY}"

if [ -z "$TAVILY_KEY" ]; then
    echo "❌ Error: TAVILY_API_KEY is not set in .env"
    exit 1
fi

# Search topics
TOPICS=("AI" "LLM" "OpenAI" "Claude AI" "Gemini AI" "LangGraph" "AI Agent" "RAG" "China LLM" "Llama" "Hugging Face" "OpenClaw")

# Date
TODAY=$(date +%Y-%m-%d)

# Check flags
SAVE_TO_OBSIDIAN=""
SEND_EMAIL=""
for arg in "$@"; do
    case $arg in
        --save) SAVE_TO_OBSIDIAN="yes" ;;
        --send) SEND_EMAIL="yes" ;;
    esac
done

echo "=== Nightly Research: $TODAY ==="
echo "Vault: $VAULT"
echo ""

# Search each topic using Tavily
RESULT_TMP="/tmp/research_results_${TODAY}.txt"
> "$RESULT_TMP"

for topic in "${TOPICS[@]}"; do
    echo "Searching: $topic..."
    
    # Call Tavily API
    result=$(curl -s "https://api.tavily.com/search" \
        -H "Content-Type: application/json" \
        -d "{
            \"api_key\": \"$TAVILY_KEY\",
            \"query\": \"$topic\",
            \"search_depth\": \"basic\",
            \"max_results\": 3
        }" 2>/dev/null)
    
    echo "### $topic" >> "$RESULT_TMP"
    echo "" >> "$RESULT_TMP"
    
    # Parse results using python (more robust than grep/sed)
    echo "$result" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    results = data.get('results', [])
    if not results:
        print('- (No results found)')
    for r in results[:3]:
        title = r.get('title', 'No title').replace('[', '(').replace(']', ')')
        print(f\"- [{title}]({r.get('url', '')})\")
        print(f\"  {r.get('content', '')[:150]}...\")
        print()
except Exception as e:
    print(f'- Error parsing results: {e}')
" >> "$RESULT_TMP"
done

# Generate note content
NOTE_CONTENT="---
created: ${TODAY}T00:00:00
tags: [nightly-research, ai, trends]
source: Tavily API
---

# 每晚 AI 趨勢追蹤 - $TODAY

$(cat "$RESULT_TMP")

---
*自動產生 - Tavily AI Search*
"

# Save to Obsidian
if [ -n "$SAVE_TO_OBSIDIAN" ]; then
    mkdir -p "$VAULT"
    NOTE_FILE="$VAULT/$TODAY-nightly-research.md"
    echo "$NOTE_CONTENT" > "$NOTE_FILE"
    echo "✅ Saved to: $NOTE_FILE"
fi

# Send email
if [ -n "$SEND_EMAIL" ]; then
    if command -v gog &> /dev/null; then
        echo "Sending email to $RECIPIENT..."
        gog gmail send \
            --to "$RECIPIENT" \
            --subject "📡 AI 趨勢追蹤 $TODAY" \
            --body-file "$RESULT_TMP"
        echo "✅ Email sent!"
    else
        echo "⚠️ Warning: 'gog' command not found. Cannot send email."
    fi
fi

# Cleanup
rm -f "$RESULT_TMP"
echo ""
echo "Done!"
