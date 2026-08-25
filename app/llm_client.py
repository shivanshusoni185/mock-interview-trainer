"""
Thin wrapper around an LLM API for two jobs only:
  1. Generate a practice interview question for a given role/topic (optionally
     tailored to a specific resume + job description).
  2. Give feedback on a transcribed answer AFTER the user has already
     answered it out loud.

There is no "live answer suggestion" anywhere in this app. Feedback is
always generated after the recording is stopped, for the user's own
private review -- never shown to anyone else, never injected into a
real interview.

Two providers are supported, chosen via LLM_PROVIDER in .env:
  - "openai"    (default) via the openai SDK
  - "anthropic" via the anthropic SDK
Both are called through the same generate_question()/get_feedback() functions
so the rest of the app never needs to know which one is active.
"""
from app.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    MAX_CONTEXT_CHARS,
)

_openai_client = None
_anthropic_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


QUESTION_SYSTEM_PROMPT = """You are an experienced technical/behavioral interviewer
generating ONE practice interview question at a time for a candidate who is
preparing on their own. Keep it realistic, specific to the role and level given,
and output ONLY the question text, nothing else (no preamble, no numbering)."""

FEEDBACK_SYSTEM_PROMPT = """You are a supportive but honest interview coach.
You will be given an interview question and the candidate's transcribed spoken
answer. Give concise, structured feedback to help them improve for NEXT time.
Cover, briefly:
1. Content: Did they actually answer the question? Any gaps or missing points?
2. Structure: For behavioral questions, did they follow something like STAR
   (Situation, Task, Action, Result)? For technical questions, was the
   explanation logically ordered?
3. Delivery: Notable filler words, rambling, or unclear phrasing (based on the
   transcript -- note that transcripts are imperfect, so be lenient about that).
4. One concrete suggestion for a stronger answer.
Keep the whole response under 200 words. Be direct and useful, not just
encouraging."""

ANSWER_SYSTEM_PROMPT = """You are a practical interview and meeting assistant.
Given the latest detected question or request and the conversation transcript,
write a concise suggested response the user can adapt. Do not claim certainty
when the transcript is incomplete. Use first person, include concrete details
only when supported by the transcript or candidate context, and output only the
suggested response. Keep it under 180 words."""


def _truncate(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    text = (text or "").strip()
    if len(text) > limit:
        return text[:limit] + "\n[...truncated]"
    return text


def _build_question_prompt(role: str, level: str, topic: str, resume_text: str, jd_text: str) -> str:
    user_prompt = f"Role: {role}\nSeniority level: {level}\n"
    if topic:
        user_prompt += f"Focus topic/skill: {topic}\n"

    resume_text = _truncate(resume_text)
    jd_text = _truncate(jd_text)
    if resume_text or jd_text:
        user_prompt += (
            "\nTailor the question to the specific opportunity described below, "
            "drawing on concrete details from the resume and/or job description "
            "where relevant (e.g. a real project, tech, or requirement) instead "
            "of a generic question for the role.\n"
        )
        if resume_text:
            user_prompt += f"\nCandidate's resume:\n{resume_text}\n"
        if jd_text:
            user_prompt += f"\nTarget job description:\n{jd_text}\n"

    user_prompt += "\nGenerate one interview question."
    return user_prompt


def generate_question(role: str, level: str, topic: str = "",
                       resume_text: str = "", jd_text: str = "") -> str:
    user_prompt = _build_question_prompt(role, level, topic, resume_text, jd_text)

    if LLM_PROVIDER == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            system=QUESTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.9,
            max_tokens=120,
        )
        return response.content[0].text.strip()

    client = _get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": QUESTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


def get_feedback(question: str, transcribed_answer: str) -> str:
    user_prompt = (
        f"Interview question:\n{question}\n\n"
        f"Candidate's transcribed answer:\n{transcribed_answer or '(No speech detected.)'}"
    )

    if LLM_PROVIDER == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            system=FEEDBACK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.4,
            max_tokens=400,
        )
        return response.content[0].text.strip()

    client = _get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": FEEDBACK_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def get_direct_answer(question: str, transcript: str) -> str:
    """Generate an explicit suggested response after capture stops."""
    user_prompt = (
        f"Latest question or request:\n{question or '(Extract the latest question from the transcript.)'}\n\n"
        f"Conversation transcript:\n{transcript or '(No speech detected.)'}"
    )
    if LLM_PROVIDER == "anthropic":
        client = _get_anthropic_client()
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            system=ANSWER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.content[0].text.strip()

    client = _get_openai_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
