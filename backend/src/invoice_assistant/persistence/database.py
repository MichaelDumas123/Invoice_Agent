"""Optional async PostgreSQL connection and tenant transaction primitives."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class DatabaseNotConfigured(RuntimeError):
    pass


class Database:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn
        self.pool = None

    async def connect(self) -> None:
        if not self.dsn:
            return
        try:
            import asyncpg  # type: ignore[import-untyped]
        except ImportError as exc:
            raise DatabaseNotConfigured("Install the postgres extra to enable durable persistence") from exc
        self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            self.pool = None

    @asynccontextmanager
    async def transaction(self, workspace_id: str) -> AsyncIterator[object | None]:
        if self.pool is None:
            yield None
            return
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("SELECT set_config('app.workspace_id', $1, true)", workspace_id)
                try:
                    yield connection
                finally:
                    await connection.execute("SELECT set_config('app.workspace_id', '', true)")
