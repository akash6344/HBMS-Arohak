from fastapi import APIRouter, Depends
from pydantic import Field

from hbms.api.dependencies import get_current_principal
from hbms.domain.schemas import ApiModel, AuthenticatedPrincipal
from hbms.services.rag_service import RagService

router = APIRouter(prefix="/ai", tags=["ai"])


class RagAskRequest(ApiModel):
    hotel_id: str = Field(min_length=1)
    question: str = Field(min_length=3, max_length=1000)


class RagCitation(ApiModel):
    section: str
    page_start: int
    page_end: int
    score: float
    excerpt: str


class RagAskResponse(ApiModel):
    answer: str
    grounded: bool
    hotel_id: str
    organization_id: str
    citations: list[RagCitation]


class RagHotelOption(ApiModel):
    organization_id: str
    hotel_id: str
    hotel_name: str
    city: str
    source_file: str | None = None
    chunk_count: int = 0


@router.get("/rag/hotels", response_model=list[RagHotelOption])
async def list_rag_hotels(
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> list[RagHotelOption]:
    hotels = await RagService.list_knowledge_hotels(principal)
    return [RagHotelOption.model_validate(hotel) for hotel in hotels]


@router.post("/rag/ask", response_model=RagAskResponse)
async def ask_rag(
    payload: RagAskRequest,
    principal: AuthenticatedPrincipal = Depends(get_current_principal),
) -> RagAskResponse:
    result = await RagService.ask(
        principal,
        hotel_id=payload.hotel_id,
        question=payload.question,
    )
    return RagAskResponse(
        answer=result.answer,
        grounded=result.grounded,
        hotel_id=result.hotel_id,
        organization_id=result.organization_id,
        citations=[
            RagCitation(
                section=c.section,
                page_start=c.page_start,
                page_end=c.page_end,
                score=c.score,
                excerpt=c.excerpt,
            )
            for c in result.citations
        ],
    )
