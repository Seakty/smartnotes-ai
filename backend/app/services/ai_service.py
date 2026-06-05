import json
import asyncio
import openai
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from openai import AsyncOpenAI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.note import Note
from app.services.note_service import note_service


class AIService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    def _strip_html_sync(self, html_content: str) -> str:
        return BeautifulSoup(html_content, "html.parser").get_text(separator=" ", strip=True)

    async def _strip_html(self, html_content: str) -> str:
        # Offload synchronous parsing to a separate thread
        return await asyncio.to_thread(self._strip_html_sync, html_content)

    async def _check_rate_limit(self, redis: Redis, user_id: str) -> None:
        key = f"rate:ai:{user_id}"
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 60, nx=True)
            results = await pipe.execute()
            
        current = results[0]
        if current > 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a minute.",
            )

    def _check_content_length(self, plain_text: str) -> None:
        if len(plain_text) < 50:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Note content is too short to process.",
            )
        # Upper bound check to prevent massive token usage
        if len(plain_text) > 20000:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Note content is too long to process.",
            )

    async def summarise_note(
        self,
        db: AsyncSession,
        redis: Redis,
        note_id: str,
        user_id: str,
    ) -> Note:
        note = await note_service.get_note(db, note_id, user_id)
        await self._check_rate_limit(redis, user_id)
        
        plain_text = await self._strip_html(note.content)
        self._check_content_length(plain_text)

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=512,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that summarises personal notes concisely. "
                            "Write a summary in 2-3 sentences maximum. Focus on the key points and "
                            "main ideas. Write in plain text — no markdown, no bullet points. "
                            "Respond with only the summary, nothing else."
                        ),
                    },
                    {"role": "user", "content": plain_text},
                ],
            )
        except openai.RateLimitError:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                detail="AI service is currently overwhelmed. Try again later."
            )
        except openai.OpenAIError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail="AI service is temporarily unavailable."
            )

        summary = response.choices[0].message.content.strip()
        note.summary = summary
        
        # Flush stages the changes; the get_db dependency handles the final commit
        await db.flush()
        await db.refresh(note)
        return note

    async def suggest_tags(
        self,
        db: AsyncSession,
        redis: Redis,
        note_id: str,
        user_id: str,
    ) -> Note:
        note = await note_service.get_note(db, note_id, user_id)
        await self._check_rate_limit(redis, user_id)
        
        plain_text = await self._strip_html(note.content)
        self._check_content_length(plain_text)

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=256,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that suggests relevant tags for personal notes. "
                            "Suggest between 3 and 5 short, lowercase tags. Tags should be single words "
                            "or short hyphenated phrases. Respond with ONLY a JSON object containing a "
                            "single key 'tags' mapped to an array of strings. "
                            'Example: {"tags": ["productivity", "work", "meeting-notes"]}. '
                            "Do not include any other text or markdown."
                        ),
                    },
                    {"role": "user", "content": f"Title: {note.title}\nContent: {plain_text}"},
                ],
            )
        except openai.RateLimitError:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, 
                detail="AI service is currently overwhelmed. Try again later."
            )
        except openai.OpenAIError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY, 
                detail="AI service is temporarily unavailable."
            )

        try:
            parsed_data = json.loads(response.choices[0].message.content)
            tags = parsed_data.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            tags = [str(t).lower().strip() for t in tags if t][:5]
        except json.JSONDecodeError:
            tags = []

        merged = list(dict.fromkeys(note.tags + tags))[:10]
        note.tags = merged
        
        # Flush stages the changes; the get_db dependency handles the final commit
        await db.flush()
        await db.refresh(note)
        return note


ai_service = AIService()