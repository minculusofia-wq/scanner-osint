"""Shared singleton service instances.

Import from here instead of creating new instances — avoids duplicate state.
"""
from app.services.osint_service import OSINTService
from app.services.osint_config_service import OSINTConfigService

osint_service = OSINTService()
config_service = OSINTConfigService()
