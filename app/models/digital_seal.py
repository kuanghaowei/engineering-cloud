"""DigitalSeal Model"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.models.base import Base


class DigitalSeal(Base):
    """
    DigitalSeal model representing a user's electronic seal/stamp.
    
    Stores references to seal images and CA certificates
    for PDF document signing and legal evidence.
    """
    __tablename__ = 'digital_seals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    seal_name = Column(String(255), nullable=False)
    seal_image_key = Column(String(500), nullable=False)  # Object storage key for seal image
    certificate_hash = Column(String(64), nullable=False)  # SHA-256 of CA certificate
    certificate_key = Column(String(500), nullable=False)  # Object storage key for certificate
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="digital_seals")
    
    def __repr__(self):
        return f"<DigitalSeal(id={self.id}, user_id={self.user_id}, name='{self.seal_name}', active={self.is_active})>"
