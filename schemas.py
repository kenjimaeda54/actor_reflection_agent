from pydantic import BaseModel, Field


class Reflection(BaseModel):
    missing: str = Field(description="Critique of what is missing")
    superfluous: str = Field(description="Critique of what is superfluous")



#As description de cada Field são enviadas à model como instrução. Elas dizem
# o que colocar em cada campo. Por isso são importantes.
# Sem AnswerQuestion não saberia responder
class AnswerQuestion(BaseModel):
    """Answer the question"""


    answer: str = Field(description="~250 word detail answer to the question")
    reflection: Reflection = Field(description="Your reflection on the initial answer")
    search_queries: list[str] = Field(
        description="1 - 3 search queries for researching improvements to address the critique of your current answer"
    )