"""SQLAlchemy ORM models — 14 tables from foundation tech spec."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Import all models to register with Base.metadata
from app.models.elder import Elder, ElderProfile  # noqa: E402, F401
from app.models.configurator import Configurator, ElderConfigurator  # noqa: E402, F401
from app.models.conversation import Conversation, Message  # noqa: E402, F401
from app.models.trigger import TriggerRule, TriggerLog  # noqa: E402, F401
from app.models.task import Task  # noqa: E402, F401
from app.models.tag import ConversationTag  # noqa: E402, F401
from app.models.unmet_need import UnmetNeed  # noqa: E402, F401
