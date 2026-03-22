import os
import json
import logging
import asyncio
from typing import Optional
from pathlib import Path

# Tentative import to avoid crashing if library didn't install correctly
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
        self.client: Optional[NotebookLMClient] = None
        self._is_ready = False

    def check_auth(self) -> bool:
        """Check if the user has performed 'notebooklm login' in their terminal."""
        if not self.STORAGE_PATH.exists():
            return False
        return True

    async def _ensure_client(self):
        """Lazy init of the client using stored credentials."""
        if self.client:
            return
        
        if not self.check_auth():
            raise Exception("NotebookLM non connecté. Veuillez lancer 'notebooklm login' une fois sur votre Mac.")
            
        if NotebookLMClient is None:
            raise Exception("S'il vous plaît installez 'notebooklm-py' via pip.")
            
        try:
            # The library likely picks up the storage.json automatically if initialized without args, 
            # but we can also pass it if the API allows.
            self.client = NotebookLMClient()
            self._is_ready = True
        except Exception as e:
            logger.error(f"Erreur d'initialisation NotebookLM: {e}")
            raise

    async def sync_alpha_signals(self, signals: list[dict]) -> str:
        """Upload latest alpha signals as a combined text source to NotebookLM."""
        await self._ensure_client()
        
        # 1. Look for existing notebook or create new one
        notebooks = await self.client.list_notebooks()
        target = next((nb for nb in notebooks if nb.title == self.DEFAULT_NOTEBOOK_NAME), None)
        
        if not target:
            target = await self.client.create_notebook(self.DEFAULT_NOTEBOOK_NAME)
            
        # 2. Format signals into a text blob
        content = "Rapport d'Intelligence OSINT - Alpha Terminal\n"
        content += "="*40 + "\n\n"
        for s in signals:
            content += f"TITRE: {s.get('ai_title') or s.get('title')}\n"
            content += f"REGION: {s.get('region')}\n"
            content += f"ANALYSE: {s.get('ai_situation')}\n"
            content += f"EDGE: {s.get('ai_analysis')}\n"
            content += f"SIGNAL: {s.get('ai_trading_signal')}\n"
            content += "-"*20 + "\n"
            
        # 3. Add source (text) - using a timestamped title
        source_title = f"Digest_{os.urandom(4).hex()}"
        await self.client.add_source(target.id, title=source_title, text=content)
        
        return target.id

    async def generate_deep_dive_podcast(self, notebook_id: str) -> str:
        """Trigger the 'Audio Overview' (Deep Dive) generation."""
        await self._ensure_client()
        
        # Generate audio overview
        # Note: the library method might be slightly different depending on version
        try:
            audio_job = await self.client.generate_audio_overview(notebook_id)
            return f"https://notebooklm.google.com/notebook/{notebook_id}"
        except Exception as e:
            logger.error(f"Génération Audio Échouée: {e}")
            raise
