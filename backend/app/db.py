from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional
from .config import settings


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    disease_input: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reasoning_log: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    targets: Mapped[list["Target"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Target(Base):
    __tablename__ = "targets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    uniprot_id: Mapped[str] = mapped_column(String)
    protein_name: Mapped[str] = mapped_column(String)
    druggability_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)

    job: Mapped["Job"] = relationship(back_populates="targets")
    structures: Mapped[list["Structure"]] = relationship(back_populates="target", cascade="all, delete-orphan")


class Structure(Base):
    __tablename__ = "structures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("targets.id"))
    pdb_path: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)  # PDB or AlphaFold
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pocket_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    target: Mapped["Target"] = relationship(back_populates="structures")
    docking_results: Mapped[list["DockingResult"]] = relationship(back_populates="structure", cascade="all, delete-orphan")


class DockingResult(Base):
    __tablename__ = "docking_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    structure_id: Mapped[int] = mapped_column(ForeignKey("structures.id"))
    molecule_smiles: Mapped[str] = mapped_column(String)
    molecule_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    binding_affinity: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    lipinski_pass: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    toxicity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    absorption_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    synthesis_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_approved_drug: Mapped[bool] = mapped_column(Boolean, default=False)
    mechanism_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    structure: Mapped["Structure"] = relationship(back_populates="docking_results")


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
