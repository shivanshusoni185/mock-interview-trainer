"""
Thin wrapper around the OpenAI API for two jobs only:
  1. Generate a practice interview question for a given role/topic.
  2. Give feedback on a transcribed answer AFTER the user has already
     answered it out loud.

There is no "live answer suggestion" anywhere in this app. Feedback is
always generated after the recording is stopped, for the user's own
private review -- never shown to anyone else, never injected into a
real interview.
"""
from openai import OpenAI

from app.config import OPENAI_API_KEY, OPENAI_MODEL

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


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


def generate_question(role: str, level: str, topic: str = "") -> str:
    client = _get_client()
    user_prompt = f"Role: {role}\nSeniority level: {level}\n"
    if topic:
        user_prompt += f"Focus topic/skill: {topic}\n"
    user_prompt += "Generate one interview question."

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
    client = _get_client()
    user_prompt = (
        f"Interview question:\n{question}\n\n"
        f"Candidate's transcribed answer:\n{transcribed_answer or '(No speech detected.)'}"
    )
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
