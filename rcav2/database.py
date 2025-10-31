# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines a data model to store the reports
"""

import datetime

from sqlalchemy.exc import NoResultFound
from sqlalchemy import Engine, func, create_engine, select, update
from sqlalchemy.orm import mapped_column, DeclarativeBase, Mapped, Session


class Base(DeclarativeBase):
    pass


class Report(Base):
    """The report table"""

    __tablename__ = "rca_reports"

    build: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    workflow: Mapped[str] = mapped_column(primary_key=True)
    events: Mapped[str | None]


class Job(Base):
    """The job table"""

    __tablename__ = "job_descriptions"

    name: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    body: Mapped[str | None]


def create(path: str) -> Engine:
    """Create the engine."""
    engine = create_engine(f"sqlite:///{path}", echo=True)
    Base.metadata.create_all(engine)
    return engine


def get_job(engine: Engine, name: str) -> str | None:
    """Get a job description from the database."""
    with Session(engine) as session:
        try:
            job = session.scalars(select(Job).where(Job.name == name)).one()
            age = datetime.datetime.now() - job.created_at
            if age.total_seconds() > 3600 * 24:
                # Ignore old job
                return None
            return job.body
        except NoResultFound:
            # Prepare a new entry
            session.add(Job(name=name))
            session.commit()
            return None


def set_job(engine: Engine, name: str, body: str):
    """Store a job description in the database."""
    with Session(engine) as session:
        session.execute(
            update(Job)
            .where(Job.name == name)
            .values(body=body, created_at=datetime.datetime.now())
        )
        session.commit()


def get(engine: Engine, workflow: str, build: str) -> str | None:
    """Get a rca report from the database."""
    with Session(engine) as session:
        try:
            report = session.scalars(
                select(Report).where(Report.build == build, Report.workflow == workflow)
            ).one()
            return report.events
        except NoResultFound:
            # Prepare a new entry
            report = Report(build=build, workflow=workflow)
            session.add(report)
            session.commit()
            return None


def set(engine: Engine, workflow: str, build: str, events: str):
    """Store a rca report in the database."""
    with Session(engine) as session:
        session.execute(
            update(Report)
            .where(Report.build == build, Report.workflow == workflow)
            .values(events=events)
        )
        session.commit()
