"""
ORM models for FinScore PME — v2.

Tables:
  - users                  : Authentication & role management
  - pme_profiles           : SME company information
  - bank_profiles          : Bank employee identity (1-to-1 with User where role=BANK)
  - financial_data         : Per-submission financial & behavioral features
  - score_reports          : ML scoring results with SHAP explanations
  - wishlists              : Banker bookmarks for PME profiles
  - banker_simulation_logs : Banker simulation history

Changes from v1:
  - BankProfile added (1-to-1 with User for BANK role)
  - Proper enums: VisibilityStatus, MarketplaceStatus, RiskTier
  - BankerSimulationLog.pme_profile_id is now optional FK (nullable)
  - ScoreReport.pme_profile_id kept as deliberate denormalisation for performance
  - UserRole extended with ADMIN
  - Domain methods added to User, PMEProfile, ScoreReport
  - ScoringService added as a pure domain-service class (not persisted)
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import relationship

from core.database import Base


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    PME   = "PME"
    BANK  = "BANK"
    ADMIN = "ADMIN"


class VisibilityStatus(str, enum.Enum):
    PRIVATE = "PRIVATE"
    PUBLIC  = "PUBLIC"


class MarketplaceStatus(str, enum.Enum):
    DRAFT     = "DRAFT"
    PUBLISHED = "PUBLISHED"
    FEATURED  = "FEATURED"


class RiskTier(str, enum.Enum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id              = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole), nullable=False, default=UserRole.PME)
    credits         = Column(Integer, default=5, nullable=False)
    created_at      = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    pme_profile     = relationship("PMEProfile", back_populates="user", uselist=False)
    bank_profile    = relationship("BankProfile", back_populates="user", uselist=False)
    wishlists       = relationship("Wishlist", back_populates="user")
    simulation_logs = relationship("BankerSimulationLog", back_populates="user")

    def authenticate(self, plain_password: str) -> bool:
        """Verify a plain-text password against the stored hash."""
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"])
        return ctx.verify(plain_password, self.hashed_password)

    def deduct_credit(self) -> None:
        """Consume one credit from the wallet; raises if insufficient."""
        if self.credits <= 0:
            raise ValueError("Insufficient credits")
        self.credits -= 1


# ---------------------------------------------------------------------------
# PME Profile
# ---------------------------------------------------------------------------

class PMEProfile(Base):
    __tablename__ = "pme_profiles"

    id                     = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                    nullable=False, unique=True)
    company_name           = Column(String(255), nullable=False)
    identifiant_unique_rne = Column(String(100), nullable=True, index=True)  # NULL != NULL in SQLite
    sector                 = Column(String(100), nullable=True)
    governorate            = Column(String(100), nullable=True)

    # Enum columns replace raw String / Integer
    visibility_status  = Column(Enum(VisibilityStatus),  default=VisibilityStatus.PRIVATE,  nullable=False)
    marketplace_status = Column(Enum(MarketplaceStatus), default=MarketplaceStatus.DRAFT,   nullable=False)

    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50),  nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user            = relationship("User", back_populates="pme_profile")
    financial_data  = relationship("FinancialData", back_populates="pme_profile",
                                   order_by="FinancialData.created_at.desc()")
    score_reports   = relationship("ScoreReport", back_populates="pme_profile",
                                   order_by="ScoreReport.created_at.desc()")
    wishlists       = relationship("Wishlist", back_populates="pme_profile")
    simulation_logs = relationship("BankerSimulationLog", back_populates="pme_profile")

    def publish(self) -> None:
        """Make the profile visible and published on the marketplace."""
        self.marketplace_status = MarketplaceStatus.PUBLISHED
        self.visibility_status  = VisibilityStatus.PUBLIC

    def suspend(self) -> None:
        """Retract the profile from the marketplace."""
        self.marketplace_status = MarketplaceStatus.DRAFT
        self.visibility_status  = VisibilityStatus.PRIVATE


# ---------------------------------------------------------------------------
# Bank Profile  (NEW — v2)
# ---------------------------------------------------------------------------

class BankProfile(Base):
    __tablename__ = "bank_profiles"

    id             = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, unique=True)
    bank_name      = Column(String(255), nullable=False)
    branch_code    = Column(String(50),  nullable=True)
    approval_level = Column(Integer, default=1, nullable=False)  # 1=Junior 2=Senior 3=Director
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="bank_profile")


# ---------------------------------------------------------------------------
# Financial Data
# ---------------------------------------------------------------------------

class FinancialData(Base):
    __tablename__ = "financial_data"

    id             = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pme_profile_id = Column(Uuid(as_uuid=True), ForeignKey("pme_profiles.id", ondelete="CASCADE"),
                            nullable=False)

    # Financial features (Model 1)
    business_turnover_tnd = Column(Float,   nullable=False)
    business_expenses_tnd = Column(Float,   nullable=False)
    profit_margin         = Column(Float,   nullable=True)
    nbr_of_workers        = Column(Integer, nullable=False, default=0)
    workers_verified_cnss = Column(Integer, nullable=False, default=0)
    formal_worker_ratio   = Column(Float,   nullable=True,  default=0.0)
    business_age_years    = Column(Integer, nullable=False, default=0)
    number_of_owners      = Column(Integer, nullable=False, default=1)

    # Behavioral features (Model 2)
    compliance_rne_score   = Column(Float,        nullable=True)
    steg_sonede_score      = Column(Float,        nullable=True)
    banking_maturity_score = Column(Float,        nullable=True)
    followers_fcb          = Column(Integer,      nullable=True, default=0)
    followers_insta        = Column(Integer,      nullable=True, default=0)
    followers_linkedin     = Column(Integer,      nullable=True, default=0)
    posts_per_month        = Column(Integer,      nullable=True, default=0)
    type_of_business       = Column(String(100),  nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    pme_profile  = relationship("PMEProfile", back_populates="financial_data")
    score_report = relationship("ScoreReport", back_populates="financial_data", uselist=False)


# ---------------------------------------------------------------------------
# Score Report
# ---------------------------------------------------------------------------

class ScoreReport(Base):
    __tablename__ = "score_reports"

    id                = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    financial_data_id = Column(Uuid(as_uuid=True), ForeignKey("financial_data.id", ondelete="CASCADE"),
                               nullable=False)
    # Deliberate denormalisation: avoids JOIN through financial_data for dashboard queries
    pme_profile_id    = Column(Uuid(as_uuid=True), ForeignKey("pme_profiles.id", ondelete="CASCADE"),
                               nullable=False)

    fin_score              = Column(Integer,          nullable=False)
    risk_tier              = Column(Enum(RiskTier),   nullable=False)   # enum replaces raw String
    decision               = Column(String(100),      nullable=True)
    decision_explanation   = Column(Text,             nullable=True)
    shap_explanations_json = Column(Text,             nullable=True)    # JSON: strengths/weaknesses

    # Persisted calculated indices for traffic-light reporting UI
    cnss_score_grade   = Column(String(20), nullable=True)  # High Compliance / Minor Issues / High Risk
    op_integrity_index = Column(String(20), nullable=True)  # Derived from RNE/STEG metrics

    model1_probability  = Column(Float, nullable=True)
    model2_probability  = Column(Float, nullable=True)
    stacked_probability = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    financial_data = relationship("FinancialData", back_populates="score_report")
    pme_profile    = relationship("PMEProfile",    back_populates="score_reports")

    def get_summary(self) -> str:
        """Return a human-readable one-liner for this report."""
        return (
            f"Score: {self.fin_score} | "
            f"Risk: {self.risk_tier.value} | "
            f"Decision: {self.decision}"
        )


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

class Wishlist(Base):
    __tablename__ = "wishlists"

    id             = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id        = Column(Uuid(as_uuid=True), ForeignKey("users.id",        ondelete="CASCADE"), nullable=False)
    pme_profile_id = Column(Uuid(as_uuid=True), ForeignKey("pme_profiles.id", ondelete="CASCADE"), nullable=False)
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user        = relationship("User",       back_populates="wishlists")
    pme_profile = relationship("PMEProfile", back_populates="wishlists")


# ---------------------------------------------------------------------------
# Banker Simulation Log
# ---------------------------------------------------------------------------

class BankerSimulationLog(Base):
    __tablename__ = "banker_simulation_logs"

    id      = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Optional FK: NULL = off-platform simulation; set = linked to existing PME on platform
    pme_profile_id = Column(Uuid(as_uuid=True), ForeignKey("pme_profiles.id", ondelete="SET NULL"),
                            nullable=True)

    company_name = Column(String(255),    nullable=False)   # always required
    capital      = Column(Float,          nullable=False)
    score        = Column(Integer,        nullable=False)
    risk_tier    = Column(Enum(RiskTier), nullable=False)   # enum replaces raw String
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    user        = relationship("User",       back_populates="simulation_logs")
    pme_profile = relationship("PMEProfile", back_populates="simulation_logs")


# ---------------------------------------------------------------------------
# ScoringService  (Domain Service — not persisted in DB)
# ---------------------------------------------------------------------------

class ScoringService:
    """
    Encapsulates ML scoring logic, keeping ScoreReport a pure data class.
    Applies the Single Responsibility Principle: the ORM models manage
    persistence; this service manages computation.
    """

    def compute_score(self, data: FinancialData) -> ScoreReport:
        """Call the ML predictor and build a ScoreReport from FinancialData."""
        from ml_services.predictor import ModelLoader
        loader = ModelLoader()
        result = loader.predict(data)

        return ScoreReport(
            financial_data_id      = data.id,
            pme_profile_id         = data.pme_profile_id,
            fin_score              = result["fin_score"],
            risk_tier              = RiskTier(result["risk_tier"]),
            decision               = result["decision"],
            decision_explanation   = result["explanation"],
            shap_explanations_json = result["shap_json"],
            model1_probability     = result["model1_prob"],
            model2_probability     = result["model2_prob"],
            stacked_probability    = result["stacked_prob"],
        )

    def run_simulation(
        self,
        capital: float,
        data: "FinancialData",
        user_id: uuid.UUID,
        pme_profile_id: uuid.UUID = None,
    ) -> BankerSimulationLog:
        """Run a quick simulation without persisting a full ScoreReport."""
        report = self.compute_score(data)
        company = (
            data.pme_profile.company_name if pme_profile_id else "Off-platform"
        )
        return BankerSimulationLog(
            user_id        = user_id,
            pme_profile_id = pme_profile_id,
            company_name   = company,
            capital        = capital,
            score          = report.fin_score,
            risk_tier      = report.risk_tier,
        )
