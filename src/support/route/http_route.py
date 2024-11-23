import fastapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.users.models import UserRole
from src.users.route import get_current_active_user
from src.users.schemas import ReadProfile

from ..models import Message, Ticket
from ..schemas import CreateTicket, ReadTicket, ReadMessage

router = fastapi.APIRouter(prefix="/tickets")


@router.post(
    '/',
    tags=['Tickets']
)
async def create_ticket(
    ticket: CreateTicket,
    user: ReadProfile = fastapi.Depends(get_current_active_user),
    db: AsyncSession = fastapi.Depends(get_session)
):
    db_ticket = Ticket(
        subject=ticket.subject,
        user_id=user.id
    )
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    db_message = Message(
        content=ticket.message,
        from_id=user.id,
        ticket_id=db_ticket.id
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    db_message.created_at = str(db_message.created_at)
    print(db_message.__dict__)
    return ReadTicket.model_validate(db_ticket)


@router.get('/', tags=['Tickets'])
async def read_tickets(
    limit: int = fastapi.Query(5, le=30),
    page: int = fastapi.Query(1),
    user: ReadProfile = fastapi.Depends(get_current_active_user),
    db: AsyncSession = fastapi.Depends(get_session)
):
    if user.role in [UserRole.admin, UserRole.support]:
        result = await db.execute(
            select(Ticket)
            .order_by(Ticket.updated_at)
            .offset((page - 1) * limit).limit(limit)
        )
    else:
        result = await db.execute(
            select(Ticket)
            .where(Ticket.user_id == user.id)
            .order_by(Ticket.updated_at)
            .offset((page - 1) * limit).limit(limit)
        )
    tickets = result.scalars()
    return [ReadTicket.model_validate(t) for t in tickets]


@router.get('/all', tags=['Tickets'])
async def read_all_tickets(
    limit: int = fastapi.Query(5, le=30),
    page: int = fastapi.Query(1),
    db: AsyncSession = fastapi.Depends(get_session)
):
    # Получаем все тикеты с пагинацией
    result = await db.execute(
        select(Ticket)
        .order_by(Ticket.updated_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    tickets = result.scalars()
    return [ReadTicket.model_validate(t) for t in tickets]


@router.get('/{ticket_id}', tags=['Tickets'])
async def read_ticket(
    ticket_id: int,
    user: ReadProfile = fastapi.Depends(get_current_active_user),
    db: AsyncSession = fastapi.Depends(get_session)
):
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    db_ticket = result.scalar_one_or_none()
    return ReadTicket.model_validate(db_ticket)


@router.patch(
    '/{ticket_id}/status',
    tags=['Tickets']
)
async def change_ticket_status(
    ticket_id: int,
    user: ReadProfile = fastapi.Depends(get_current_active_user),
    db: AsyncSession = fastapi.Depends(get_session)
):
    db_ticket = await db.get(Ticket, ticket_id)
    # Check user is an admin
    is_admin = user.role == UserRole.admin
    # Check ticket belongs to the user
    is_ticket_of_user = db_ticket.user_id == user.id
    if not (is_admin or is_ticket_of_user):
        return fastapi.HTTPException(
            401,
            'Not enough rights to update ticket status',
        )
    db_ticket.status = fastapi.status
    await db.commit()
    await db.refresh(db_ticket)
    return ReadTicket.model_validate(db_ticket)


@router.get('/messages/{ticket_id}/', tags=['Tickets'])
async def get_messages(
    ticket_id: int,
    limit: int = fastapi.Query(5, le=30),
    page: int = fastapi.Query(1),
    user: ReadProfile = fastapi.Depends(get_current_active_user),
    db: AsyncSession = fastapi.Depends(get_session)
):
    result = await db.execute(
        select(Message).where(
            Message.ticket_id == ticket_id
        )
        .order_by(Message.created_at.desc())
        .offset((page - 1) * limit).limit(limit)
    )
    return [
        ReadMessage.model_validate(entry)
        for entry in result.scalars()
    ]
