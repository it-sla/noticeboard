import os

from sqlalchemy import create_engine

from alembic import context
from app.core.config import get_settings
from app.models import Base

target_metadata = Base.metadata


def run() -> None:
    # Production migrates as the schema owner; the app itself runs as a restricted role.
    url = os.environ.get("MIGRATE_DATABASE_URL") or get_settings().database_url
    if context.is_offline_mode():
        context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(url)
    with engine.connect() as conn:
        context.configure(
            connection=conn,
            target_metadata=target_metadata,
            render_as_batch=url.startswith("sqlite"),
        )
        with context.begin_transaction():
            context.run_migrations()


run()
