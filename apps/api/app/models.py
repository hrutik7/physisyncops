from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uuid() -> str:
    return str(uuid4())


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    snapshots: Mapped[list["BusinessSnapshot"]] = relationship(back_populates="brand")


class MappingTemplate(Base):
    __tablename__ = "mapping_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    upload_source: Mapped[str] = mapped_column(String(80), nullable=False)
    mapping: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BusinessSnapshot(Base):
    __tablename__ = "business_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    upload_source: Mapped[str] = mapped_column(String(80), nullable=False)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)

    brand: Mapped[Brand] = relationship(back_populates="snapshots")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="snapshot")


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("business_snapshots.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    business_impact: Mapped[float | None] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    affected_campaigns: Mapped[list] = mapped_column(JSON, default=list)
    affected_skus: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(String(32), default="pending")
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # UI Rich Fields and Ontology Layer
    impact_label: Mapped[str | None] = mapped_column(String(240))
    cross_system_signals: Mapped[list] = mapped_column(JSON, default=list)
    risk_projection: Mapped[list] = mapped_column(JSON, default=list)
    recommended_actions: Mapped[list] = mapped_column(JSON, default=list)
    verification_signals: Mapped[list] = mapped_column(JSON, default=list)
    confidence_explanation: Mapped[str | None] = mapped_column(Text)
    relationship_edges: Mapped[list] = mapped_column(JSON, default=list)

    snapshot: Mapped[BusinessSnapshot] = relationship(back_populates="decisions")


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="recommended")
    expected_effect: Mapped[dict] = mapped_column(JSON, default=dict)
    verification_metric: Mapped[dict] = mapped_column(JSON, default=dict)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UnitEconomics(Base):
    __tablename__ = "unit_economics"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    sku_id: Mapped[str | None] = mapped_column(String(120), index=True)
    gross_margin_percent: Mapped[float] = mapped_column(Float, default=35)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0)
    cod_fee: Mapped[float] = mapped_column(Float, default=0)
    rto_cost: Mapped[float] = mapped_column(Float, default=0)
    discount_cost: Mapped[float] = mapped_column(Float, default=0)
    payment_gateway_cost: Mapped[float] = mapped_column(Float, default=0)
    packaging_cost: Mapped[float] = mapped_column(Float, default=0)
    average_order_value: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BrandGoal(Base):
    __tablename__ = "brand_goals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    goal_type: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    target: Mapped[dict] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OntologyNode(Base):
    __tablename__ = "ontology_nodes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(200), index=True)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OntologyEdge(Base):
    __tablename__ = "ontology_edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    from_key: Mapped[str] = mapped_column(String(200), index=True)
    to_key: Mapped[str] = mapped_column(String(200), index=True)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    strength: Mapped[str] = mapped_column(String(24), default="medium")
    source_decision_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ConnectorEvent(Base):
    __tablename__ = "connector_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("business_snapshots.id"), index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_key: Mapped[str | None] = mapped_column(String(200), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VerificationScorecard(Base):
    __tablename__ = "verification_scorecards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    intervention_id: Mapped[str] = mapped_column(ForeignKey("interventions.id"), index=True)
    decision_id: Mapped[str] = mapped_column(ForeignKey("decisions.id"), index=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    metrics: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
