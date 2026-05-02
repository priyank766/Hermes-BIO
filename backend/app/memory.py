"""Persistent harness memory.

Deliberate memory, not emergent: the harness decides what gets remembered, not
the agent. Used to make repeat runs on the same disease class faster + more
informed.

Keyed by (scope, key). Scope is namespace (e.g. 'drug_discovery'); key is a
normalized identifier (e.g. 'disease:type-2-diabetes-mellitus').
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .db import HarnessMemory, SessionLocal


# ----- Key normalization ---------------------------------------------------

def normalize_disease(disease: str) -> str:
    """Collapse whitespace, lowercase, strip punctuation. Idempotent."""
    s = disease.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def disease_key(disease: str) -> str:
    return f"disease:{normalize_disease(disease)}"


def uniprot_key(uniprot_id: str) -> str:
    return f"uniprot:{uniprot_id.upper()}"


def pdb_key(pdb_id: str) -> str:
    return f"pdb:{pdb_id.upper()}"


# ----- CRUD ----------------------------------------------------------------

async def get(scope: str, key: str, *, session: Optional[AsyncSession] = None) -> Optional[dict]:
    async def _do(s: AsyncSession) -> Optional[dict]:
        stmt = select(HarnessMemory).where(
            HarnessMemory.scope == scope, HarnessMemory.key == key
        )
        row = (await s.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        if row.expires_at and row.expires_at < datetime.utcnow():
            await s.delete(row)
            await s.commit()
            return None
        return {
            "value": row.value,
            "created_at": row.created_at.isoformat(),
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }
    if session:
        return await _do(session)
    async with SessionLocal() as s:
        return await _do(s)


async def put(scope: str, key: str, value: Any, *, ttl: Optional[timedelta] = None) -> None:
    async with SessionLocal() as s:
        stmt = select(HarnessMemory).where(
            HarnessMemory.scope == scope, HarnessMemory.key == key
        )
        row = (await s.execute(stmt)).scalar_one_or_none()
        expires_at = (datetime.utcnow() + ttl) if ttl else None
        if row:
            row.value = value
            row.created_at = datetime.utcnow()
            row.expires_at = expires_at
        else:
            s.add(HarnessMemory(scope=scope, key=key, value=value, expires_at=expires_at))
        await s.commit()


async def recall(scope: str, *, prefix: Optional[str] = None) -> list[dict]:
    async with SessionLocal() as s:
        stmt = select(HarnessMemory).where(HarnessMemory.scope == scope)
        if prefix:
            stmt = stmt.where(HarnessMemory.key.like(f"{prefix}%"))
        rows = (await s.execute(stmt)).scalars().all()
        out = []
        now = datetime.utcnow()
        for r in rows:
            if r.expires_at and r.expires_at < now:
                continue
            out.append({
                "key": r.key,
                "value": r.value,
                "created_at": r.created_at.isoformat(),
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            })
        return out


async def clear(scope: str, *, prefix: Optional[str] = None) -> int:
    async with SessionLocal() as s:
        stmt = delete(HarnessMemory).where(HarnessMemory.scope == scope)
        if prefix:
            stmt = stmt.where(HarnessMemory.key.like(f"{prefix}%"))
        res = await s.execute(stmt)
        await s.commit()
        return res.rowcount or 0


# ----- TTL presets ---------------------------------------------------------

TTL_TARGET_PICK = timedelta(days=30)
TTL_STRUCTURE = timedelta(days=90)
TTL_POCKET = timedelta(days=90)
TTL_APPROVED_HITS = timedelta(days=14)
TTL_FAILED_LOOKUP = timedelta(hours=1)
