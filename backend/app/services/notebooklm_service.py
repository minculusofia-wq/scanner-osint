"""NotebookLM Service — Bridge between OSINT scanner and Google NotebookLM.

Uses notebooklm-py async API for:
- Syncing alpha briefs as text sources
- Generating podcasts (Audio Overview)
- Generating mind maps (JSON for Knowledge Graph)
- Generating data tables (CSV export)
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from notebooklm import NotebookLMClient
except ImportError:
    NotebookLMClient = None

logger = logging.getLogger(__name__)


class NotebookLMService:
    """Service to bridge OSINT scanner with Google NotebookLM."""

    STORAGE_PATH = Path.home() / ".notebooklm" / "storage_state.json"
    DEFAULT_NOTEBOOK_NAME = "Alpha Terminal OSINT Digest"

    def __init__(self):
        self._client: Optional["NotebookLMClient"] = None
        self._notebook_id: Optional[str] = None

    def check_auth(self) -> bool:
        """Check if the user has performed 'notebooklm login'."""
        if NotebookLMClient is None:
            return False
        return self.STORAGE_PATH.exists()

    async def _get_client(self) -> "NotebookLMClient":
        """Lazy init of the client using stored credentials."""
        if self._client:
            return self._client

        if not self.check_auth():
            raise Exception(
                "NotebookLM non connecté. Lancez 'notebooklm login' dans votre terminal."
            )

        self._client = await NotebookLMClient.from_storage()
        return self._client

    async def _get_or_create_notebook(self) -> str:
        """Find existing OSINT notebook or create a new one. Returns notebook_id."""
        if self._notebook_id:
            return self._notebook_id

        client = await self._get_client()
        notebooks = await client.notebooks.list()
        target = next(
            (nb for nb in notebooks if nb.title == self.DEFAULT_NOTEBOOK_NAME),
            None,
        )

        if not target:
            target = await client.notebooks.create(self.DEFAULT_NOTEBOOK_NAME)
            logger.info(f"Created NotebookLM notebook: {target.id}")

        self._notebook_id = target.id
        return self._notebook_id

    async def sync_alpha_signals(self, signals: list[dict]) -> str:
        """Upload latest alpha signals as a text source to NotebookLM."""
        client = await self._get_client()
        nb_id = await self._get_or_create_notebook()

        # Format signals into text
        content = "Rapport d'Intelligence OSINT — Alpha Terminal\n"
        content += "=" * 50 + "\n\n"
        for s in signals:
            content += f"TITRE: {s.get('ai_title') or s.get('title')}\n"
            content += f"RÉGION: {s.get('region')}\n"
            content += f"CATÉGORIE: {s.get('category', '')}\n"
            content += f"SITUATION: {s.get('ai_situation', '')}\n"
            content += f"ANALYSE EDGE: {s.get('ai_analysis', '')}\n"
            content += f"SIGNAL TRADING: {s.get('ai_trading_signal', '')}\n"
            content += f"CONFIANCE: {s.get('ai_confidence', 0)}/5\n"
            content += f"RISQUES: {s.get('ai_risk_factors', '')}\n"
            content += "-" * 30 + "\n\n"

        source_title = f"Digest_{os.urandom(4).hex()}"
        await client.sources.add_text(nb_id, title=source_title, content=content)
        logger.info(f"Synced {len(signals)} signals to NotebookLM")

        return nb_id

    async def generate_podcast(self, notebook_id: str | None = None) -> str:
        """Generate Audio Overview (podcast) and return notebook URL."""
        client = await self._get_client()
        nb_id = notebook_id or await self._get_or_create_notebook()

        status = await client.artifacts.generate_audio(
            nb_id,
            instructions="Analyse en français les signaux OSINT. Style: analyste géopolitique agressif cherchant l'edge trading.",
            language="fr",
        )
        await client.artifacts.wait_for_completion(nb_id, status.task_id, timeout=300)
        logger.info(f"Podcast generated for notebook {nb_id}")

        return f"https://notebooklm.google.com/notebook/{nb_id}"

    async def generate_mind_map(self, notebook_id: str | None = None) -> dict:
        """Generate mind map and return JSON data for Knowledge Graph."""
        client = await self._get_client()
        nb_id = notebook_id or await self._get_or_create_notebook()

        status = await client.artifacts.generate_mind_map(
            nb_id,
            custom_prompt="Crée une mind map des entités clés (personnes, organisations, lieux, événements) et leurs relations.",
            language="fr",
        )

        task_id = status.task_id if hasattr(status, "task_id") else status.get("task_id", "")
        if task_id:
            await client.artifacts.wait_for_completion(nb_id, task_id, timeout=120)

        # Download mind map as JSON to temp file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            await client.artifacts.download_mind_map(nb_id, tmp_path)
            with open(tmp_path) as f:
                mind_map = json.load(f)
            logger.info(f"Mind map generated for notebook {nb_id}")
            return mind_map
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def generate_data_table(self, notebook_id: str | None = None) -> str:
        """Generate data table CSV from signals. Returns CSV content."""
        client = await self._get_client()
        nb_id = notebook_id or await self._get_or_create_notebook()

        status = await client.artifacts.generate_data_table(
            nb_id,
            instructions="Crée un tableau structuré avec: Titre, Région, Catégorie, Signal (YES/NO/HOLD), Confiance (1-5), Risques",
            language="fr",
        )
        await client.artifacts.wait_for_completion(nb_id, status.task_id, timeout=120)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            tmp_path = f.name

        try:
            await client.artifacts.download_data_table(nb_id, tmp_path)
            with open(tmp_path, encoding="utf-8-sig") as f:
                csv_content = f.read()
            logger.info(f"Data table generated for notebook {nb_id}")
            return csv_content
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def close(self):
        """Clean up client resources."""
        if self._client and hasattr(self._client, "close"):
            await self._client.close()
        self._client = None
        self._notebook_id = None
