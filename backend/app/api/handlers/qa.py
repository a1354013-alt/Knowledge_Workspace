# ruff: noqa: F401,F403,F405
from app.api.handlers.support import *  # noqa: F403


@limiter.limit("10/minute")  # Rate limit: 10 requests per minute to prevent abuse
async def qa(request: Request, payload: QARequest, current_user: dict = Depends(get_current_user)) -> QAResponse:
    _ = request
    answer, sources = await perform_qa(payload.question, current_user["sub"], db)
    logger.info("QA request by %s returned %s sources", current_user["sub"], len(sources))
    return QAResponse(answer=answer, sources=sources)


async def generate(request: GenerateRequest, current_user: dict = Depends(get_current_user)) -> GenerateResponse:
    content = await generate_form(request.template_type, request.inputs, current_user["sub"])
    return GenerateResponse(content=content)
