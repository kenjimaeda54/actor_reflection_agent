import datetime
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputToolsParser, PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from schemas import AnswerQuestion

load_dotenv()

APIKEY_OPENROUTER = os.environ.get("OPEN_ROUTER_API_KEY", "")

llm = ChatOpenRouter(
    model="z-ai/glm-5.3-flash",
    api_key=SecretStr(APIKEY_OPENROUTER),
)

parser = JsonOutputToolsParser(return_id=True)
parser_pydantic = PydanticToolsParser(tools=[AnswerQuestion])

actor_reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
             You are expert research.
             Current time: {time}

             1 - {first_instruction}
             2 - Reflect and critique your answer.Be severe to maximize improvement.
             3 - Recommend search queries to research information and improve your answer
            """
        ),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Answer the user's question above using the required format"),
    ]
).partial(
    time=lambda: datetime.datetime.now().isoformat()
)

first_responder_prompt_template = actor_reflection_prompt.partial(
    first_instruction="Provide a detailed ~250 word answer"
)

first_responder = first_responder_prompt_template | llm.bind_tools(
    tools=[AnswerQuestion], tool_choice="AnswerQuestion"
)

if __name__ == "__main__":
    human_message = HumanMessage(
        content="Write about AI-Powerd SOC / autonomous soc problem domain"
        "list startups that do that and raised capital"
    )
    chain = first_responder | parser_pydantic
    res = chain.invoke(input={"messages": [human_message]})
    print(res)
