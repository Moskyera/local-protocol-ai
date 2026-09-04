import json

from llm_agent import generate_market_report

def analyze_headline_sentiment(headline):

    prompt = f"""
You are an elite financial sentiment analyst.

Analyze this headline:

"{headline}"

Return ONLY valid JSON.

Format:

{{
    "sentiment": "POSITIVE",
    "confidence": 95,
    "reason": "short explanation"
}}
"""

    response = generate_market_report(prompt)

    try:

        data = json.loads(response)

        return data

    except Exception:

        return {
            "sentiment": "NEUTRAL",
            "confidence": 0,
            "reason": "Failed to parse AI response."
        }