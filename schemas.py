from pydantic import BaseModel, Field


class Reflection(BaseModel):
    missing: str = Field(description="Critique of what is missing")
    superfluous: str = Field(description="Critique of what is superfluous")


class AnswerQuestion(BaseModel):
    """Answer the question"""

    answer: str = Field(description="~250 word detail answer to the question")
    reflection: Reflection = Field(description="Your reflection on the initial answer")
    search_queries: list[str] = Field(
        description="1 - 3 search queries for researching improvements to address the critique of your current answer"
    )
