import enum
from datetime import datetime

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Integer, String,
                        event)
from sqlalchemy.orm import relationship

from src.db_base import Base


class TicketStatus(enum.Enum):
    open = 'open'
    closed = 'closed'


class MimeType(enum.Enum):
    jpeg = 'image/jpeg'
    png = 'image/png'
    gif = 'image/gif'
    text = 'text/plain'


class Ticket(Base):
    __tablename__ = 'tickets'
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    status = Column(Enum(TicketStatus), default=TicketStatus.open)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship('User', back_populates='tickets')
    messages = relationship('Message', back_populates='ticket')


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, default=None)
    created_at = Column(DateTime, default=datetime.now)

    from_id = Column(Integer, ForeignKey('users.id'))
    ticket_id = Column(Integer, ForeignKey('tickets.id'))

    user = relationship('User', back_populates='messages')
    ticket = relationship('Ticket', back_populates='messages')


def update_ticket_updated_at(mapper, connection, target):
    'Updates Ticket updated_at attribute when new Message created'
    if target.ticket:
        target.ticket.updated_at = datetime.now()


event.listen(Message, 'after_insert', update_ticket_updated_at)
event.listen(Message, 'after_update', update_ticket_updated_at)
