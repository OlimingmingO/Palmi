"""SQLAlchemy ORM models."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Phase 0: Only Elder model is implemented
from app.models.elder import Elder  # noqa: E402, F401
from app.models.conversation import Conversation  # noqa: E402, F401

# Phase 2: Proactive triggers and intent classification
from app.models.trigger import TriggerLog, TriggerState  # noqa: E402, F401
from app.models.tag import IntentTag, MessageTag, TagCorrection  # noqa: E402, F401

# Phase 3: Ops console + Configurator
from app.models.elder_profile import ElderProfile  # noqa: E402, F401
from app.models.configurator import Configurator  # noqa: E402, F401
from app.models.pke_query_log import PkeQueryLog  # noqa: E402, F401
from app.models.unmet_need import UnmetNeed  # noqa: E402, F401
