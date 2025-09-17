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
    __tablename__ = "rca_reports"

    build: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    events: Mapped[str | None]


def create(path: str) -> Engine:
    engine = create_engine(f"sqlite:///{path}", echo=True)
    Base.metadata.create_all(engine)
    return engine


def get(engine: Engine, build: str) -> str | None:
    with Session(engine) as session:
        try:
            report = session.scalars(select(Report).where(Report.build == build)).one()
            return report.events
        except NoResultFound:
            report = Report(build=build)
            session.add(report)
            session.commit()
            return None


def set(engine: Engine, build: str, events: str):
    with Session(engine) as session:
        session.execute(
            update(Report).where(Report.build == build).values(events=events)
        )
        session.commit()
