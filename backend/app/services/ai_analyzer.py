"""AI Analyzer — Google Gemini Flash (gratuit) pour analyse des croisements de sources.

Enriches rule-based briefs with AI-generated:
- Situation summary (factual)
- Market analysis (implications)
- Trading signal (concrete recommendation)
- Confidence level (1-5)
- Risk factors

Uses Gemini 2.0 Flash via REST API (free tier: 1500 req/day).
No external SDK needed — uses httpx already in project.
"""

import json
import logging
from collections import defaultdict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

SYSTEM_PROMPT = """Tu es un analyste OSINT senior spécialisé dans les marchés prédictifs (Polymarket).
Tu reçois des clusters de signaux d'intelligence regroupés par catégorie et région.

Pour CHAQUE cluster, fournis une analyse investissement structurée :
- situation: Résumé factuel en 2-3 phrases. Quoi, qui, où, quand. Pas de spéculation.
- analysis: Pourquoi c'est important pour les marchés. Implications géopolitiques, financières, ou sociales. Impact probable sur Polymarket. 2-3 phrases.
- trading_signal: Recommandation concrète. Direction (YES ou NO) sur quel type de marché, avec raisonnement clair. Si un marché Polymarket est lié, mentionne-le directement.
- confidence: Conviction de 1 à 5 (1=signal faible/incertain, 3=modéré, 5=très haute conviction).
- risk_factors: 1-2 facteurs qui pourraient invalider ton analyse.

Règles:
- Sois DIRECT et CONCIS. Pas de disclaimers, pas de "il est important de noter".
- Parle comme un trader à un autre trader.
- Si les signaux sont contradictoires ou trop faibles, dis-le franchement avec confidence=1-2.
- Priorise les signaux provenant de sources officielles (gov_rss, sec_edgar) et données terrain (adsb, acled, ship_tracker) par rapport aux sources média (gdelt, newsdata, reddit).
- Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks."""


class AIAnalyzer:
    """Enriches intelligence briefs with Gemini Flash analysis (free)."""

    async def analyze_briefs(
        self,
        briefs: list[dict],
        all_items: list[dict],
    ) -> dict[str, dict]:
        """Analyze briefs with Gemini Flash and return AI enrichments.

        Returns:
            Dict mapping cluster_key to AI analysis fields
        """
        if not settings.GEMINI_API_KEY:
            return {}

        if not briefs:
            return {}

        # Group items by cluster key for context
        items_by_cluster: dict[str, list[dict]] = defaultdict(list)
        for item in all_items:
            key = f"{item.get('category', 'general')}:{item.get('region', 'global') or 'global'}"
            items_by_cluster[key].append(item)

        user_prompt = self._build_prompt(briefs, items_by_cluster)

        try:
            payload = {
                "system_instruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                },
                "contents": [
                    {"parts": [{"text": user_prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4096,
                    "responseMimeType": "application/json",
                },
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": settings.GEMINI_API_KEY},
                    json=payload,
                )

            if resp.status_code != 200:
                logger.error(f"Gemini API error {resp.status_code}: {resp.text[:300]}")
                return {}

            data = resp.json()
            response_text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            if not response_text:
                logger.warning("Gemini returned empty response")
                return {}

            results = self._parse_response(response_text, briefs)
            logger.info(f"AI analysis (Gemini Flash): enriched {len(results)}/{len(briefs)} briefs")
            return results

        except httpx.TimeoutException:
            logger.warning("Gemini API timeout — skipping AI analysis")
            return {}
        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            return {}

    def _build_prompt(
        self,
        briefs: list[dict],
        items_by_cluster: dict[str, list[dict]],
    ) -> str:
        """Build the user prompt with all brief clusters."""
        parts = [f"Analyse ces {len(briefs)} clusters de signaux d'intelligence.\n"]

        for i, brief in enumerate(briefs, 1):
            key = f"{brief.get('category', 'general')}:{brief.get('region', 'global')}"
            cluster_items = items_by_cluster.get(key, [])

            # Top 5 items sorted by priority
            top_items = sorted(
                cluster_items,
                key=lambda x: x.get("priority_score", 0),
                reverse=True,
            )[:5]

            parts.append(f"\n--- Cluster {i}: \"{key}\" ---")
            parts.append(f"Priorité max: {brief.get('priority_score', 0):.0f}/100")
            parts.append(f"Nombre de signaux: {brief.get('source_count', 0)}")
            parts.append(f"Urgence: {brief.get('urgency', 'low')}")

            for item in top_items:
                source = item.get("source", "?")
                title = item.get("title", "")[:150]
                summary = item.get("summary", "")[:200]
                sentiment = item.get("sentiment_score", 0)
                priority = item.get("priority_score", 0)

                parts.append(
                    f"  [{source}] {title}"
                    f"\n    {summary}"
                    f"\n    (priorité: {priority:.0f}, sentiment: {sentiment:+.2f})"
                )

            # Add linked Polymarket markets if any
            try:
                market_questions = json.loads(
                    brief.get("linked_market_questions", "[]")
                )
                if market_questions:
                    parts.append("  Marchés Polymarket liés:")
                    for q in market_questions[:3]:
                        parts.append(f"    • {q}")
            except (json.JSONDecodeError, TypeError):
                pass

        parts.append(
            f"\n\nRéponds en JSON avec les clés exactes des clusters: "
            f"{json.dumps([f'{b.get(\"category\", \"general\")}:{b.get(\"region\", \"global\")}' for b in briefs])}"
        )

        return "\n".join(parts)

    def _parse_response(
        self, response_text: str, briefs: list[dict]
    ) -> dict[str, dict]:
        """Parse Gemini's JSON response into cluster-keyed results."""
        text = response_text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse AI response as JSON: {text[:200]}...")
            return {}

        if not isinstance(parsed, dict):
            logger.warning(f"AI response is not a dict: {type(parsed)}")
            return {}

        results = {}
        for brief in briefs:
            key = f"{brief.get('category', 'general')}:{brief.get('region', 'global')}"
            if key in parsed and isinstance(parsed[key], dict):
                entry = parsed[key]
                results[key] = {
                    "ai_situation": str(entry.get("situation", ""))[:1000],
                    "ai_analysis": str(entry.get("analysis", ""))[:1000],
                    "ai_trading_signal": str(entry.get("trading_signal", ""))[:1000],
                    "ai_confidence": min(5, max(0, int(entry.get("confidence", 0)))),
                    "ai_risk_factors": str(entry.get("risk_factors", ""))[:500],
                }

        return results
