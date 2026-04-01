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
import re
from collections import defaultdict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _sanitize_for_prompt(text: str, max_len: int = 200) -> str:
    """Strip control characters and truncate to prevent prompt injection."""
    if not text:
        return ""
    cleaned = re.sub(r"[\n\r\t]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len]


GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

SYSTEM_PROMPT = """Tu es un analyste OSINT senior spécialisé dans les marchés prédictifs (Polymarket).
Tu reçois des clusters de signaux d'intelligence regroupés par catégorie et région.

Pour CHAQUE cluster, fournis une analyse CLAIRE et STRUCTURÉE en FRANÇAIS :

- title: Titre court et factuel en français (max 12 mots). Ex: "Escalade militaire au Moyen-Orient" ou "Crise bancaire : signaux précoces en Europe".
- situation: QUE SE PASSE-T-IL ? Résumé factuel en 2 phrases maximum. Qui, quoi, où, quand. Pas de spéculation.
- analysis: POURQUOI C'EST IMPORTANT ? En 2 phrases : quel impact sur les marchés Polymarket ? Quel avantage informationnel par rapport au grand public ?
- trading_signal: QUOI FAIRE ? Une phrase claire : "YES sur [marché]" ou "NO sur [marché]" ou "ATTENDRE — pas assez de signal". Si un marché Polymarket est lié, mentionne-le. Justifie en une phrase.
- confidence: Conviction de 1 à 5. 1=bruit/rien d'actionnable, 2=signal faible, 3=signal modéré, 4=signal fort, 5=haute conviction.
- risk_factors: En une phrase : qu'est-ce qui pourrait invalider cette analyse ?

Règles ABSOLUES :
- TOUT en FRANÇAIS. Pas un seul mot en anglais dans tes analyses.
- Sois CONCIS. Phrases courtes et directes. Pas de fioritures ni de disclaimers.
- Privilégie les données terrain (adsb, ship_tracker, acled) sur les médias (gdelt, newsdata).
- CHAQUE type de signal a des marchés pertinents sur Polymarket : météo extrême → marchés catastrophes/ouragans/température, séismes → marchés catastrophes, conflits → marchés géopolitiques, économie → marchés financiers. Ne dis JAMAIS "pas de lien" sans avoir cherché le bon type de marché.
- Si les signaux sont trop faibles ou contradictoires, dis-le franchement avec confidence=1 et trading_signal="ATTENDRE".
- JSON valide uniquement, sans markdown, sans backticks.
"""

ENTITY_EXTRACTION_PROMPT = """Extraite toutes les entités importantes de cette alerte OSINT pour une base de connaissance "façon Palantir".

Liste les:
- persons: Nom complet si possible.
- organizations: Entreprises, agences gouvernementales, groupes militaires/rebelles.
- locations: Pays, villes, régions précises, sites stratégiques.
- assets: Tickers boursiers (ex: AAPL), IDs d'avions (ICAO/Tail), IDs de navires (IMO), Wallets Crypto.
- events: Type d'action (ex: missile_strike, merger_rumor, whale_transfer).

Produis un JSON structuré:
{
  "entities": [{"name": "...", "type": "person|organization|location|asset|event", "metadata": {}}],
  "relationships": [{"source": "...", "target": "...", "type": "mentions|located_in|owned_by|attacked|operates", "confidence": 0.0}]
}

Réponds UNIQUEMENT en JSON valide."""


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

            if resp.status_code == 429:
                logger.warning("Gemini API rate limited (429) — skipping AI analysis this cycle")
                return {}

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

    async def extract_entities(self, item_title: str, item_summary: str) -> dict:
        """Extract structured entities and relationships from a single item.

        Returns:
            Dict with 'entities' and 'relationships' keys.
        """
        if not settings.GEMINI_API_KEY:
            return {"entities": [], "relationships": []}

        prompt = f"Titre: {item_title}\nRésumé: {item_summary}"

        try:
            payload = {
                "system_instruction": {"parts": [{"text": ENTITY_EXTRACTION_PROMPT}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                    "responseMimeType": "application/json",
                },
            }

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": settings.GEMINI_API_KEY},
                    json=payload,
                )

            if resp.status_code != 200:
                return {"entities": [], "relationships": []}

            data = resp.json()
            response_text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )

            if not response_text:
                return {"entities": [], "relationships": []}

            # Parse and sanitize
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            
            parsed = json.loads(text.strip())
            return {
                "entities": parsed.get("entities", []),
                "relationships": parsed.get("relationships", []),
            }
        except Exception as e:
            logger.debug(f"Entity extraction failed: {e}")
            return {"entities": [], "relationships": []}

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

        cluster_keys = [
            f"{b.get('category', 'general')}:{b.get('region', 'global')}"
            for b in briefs
        ]
        parts.append(
            f"\n\nRéponds en JSON avec les clés exactes des clusters: "
            f"{json.dumps(cluster_keys)}"
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
        # Robust extraction of JSON object
        if "{" in text:
            text = text[text.find("{"):]
        if "}" in text:
            text = text[:text.rfind("}")+1]
        
        try:
            import json
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
                    "ai_title": str(entry.get("title", ""))[:150],
                    "ai_situation": str(entry.get("situation", ""))[:1000],
                    "ai_analysis": str(entry.get("analysis", ""))[:1000],
                    "ai_trading_signal": str(entry.get("trading_signal", ""))[:1000],
                    "ai_confidence": min(5, max(0, int(entry.get("confidence", 0)))),
                    "ai_risk_factors": str(entry.get("risk_factors", ""))[:500],
                }

        return results

    async def generate_chat_response(
        self, message: str, history: list[dict], context_briefs: list[dict]
    ) -> str:
        """Engage in a conversational chat using the OSINT briefs as context."""
        if not settings.GEMINI_API_KEY:
            return "Erreur : La clé API Gemini n'est pas configurée dans le backend."

        system_prompt = (
            "Tu es l'assistant de l'Alpha Terminal (Scanner OSINT). "
            "Tu es un expert en analyse géopolitique, renseignement terrain (SDR/ADSB) et marchés prédictifs.\n"
            "CONTEXTE ACTUEL (Dernières alertes) :\n"
        )
        
        for b in context_briefs[:15]:
            title = _sanitize_for_prompt(b.get('title', ''), 150)
            summary = _sanitize_for_prompt(b.get('summary', ''), 300)
            analysis = _sanitize_for_prompt(b.get('ai_analysis', ''), 300)
            signal = _sanitize_for_prompt(b.get('ai_trading_signal', ''), 200)
            system_prompt += (
                f"<source_brief>[{b.get('category')} / {b.get('region')}] "
                f"{title} | Info: {summary} | Edge: {analysis} | Signal: {signal}"
                f"</source_brief>\n"
            )
            
        system_prompt += (
            "RÈGLES :\n"
            "1. Tu DOIS toujours répondre en FRANÇAIS.\n"
            "2. Si l'utilisateur pose une question sur un événement récent, base-toi sur le CONTEXTE ACTUEL.\n"
            "3. Sois concis, analytique, et oriente toujours tes réponses pour trouver 'l'Edge' d'investissement (Polymarket, Crypto, Bourse).\n"
            "4. Tu peux utiliser du Markdown pour formater ta réponse."
        )

        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })

        try:
            payload = {
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048,
                },
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GEMINI_URL,
                    params={"key": settings.GEMINI_API_KEY},
                    json=payload,
                )

            if resp.status_code != 200:
                return f"Erreur API Gemini : {resp.status_code} - {resp.text}"
                
            data = resp.json()
            response_text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "Désolé, je n'ai pas de réponse.")
            )
            return response_text
            
        except Exception as e:
            logger.error(f"Chat generation failed: {e}", exc_info=True)
            return "Erreur de connexion au modèle IA."
