import os
import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputToolsParser, PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from schemas import AnswerQuestion, ReviseAnswer

load_dotenv()

APIKEY_OPENROUTER = os.environ.get("OPEN_ROUTER_API_KEY","")


llm = ChatOpenRouter(
    model="z-ai/glm-5.3-flash",
    api_key=SecretStr(APIKEY_OPENROUTER)
)

paser = JsonOutputToolsParser(return_id=True)
pydantic_paser = PydanticToolsParser(tools=[AnswerQuestion])

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

first_responder_template = actor_reflection_prompt.partial(
    first_instruction="Provide a detailed ~250 words answer"
)
first_responder = first_responder_template | llm.bind_tools(
    tools=[AnswerQuestion], tool_choice="AnswerQuestion"
)

revise_instructions = """Revise your previous answer using the new information.
    - You should use the previous critique to add important information to your answer.
        - You MUST include numerical citations in your revised answer to ensure it can be verified.
        - Add a "References" section to the bottom of your answer (which does not count towards the word limit). In form of:
            - [1] https://example.com
            - [2] https://example.com
    - You should use the previous critique to remove superfluous information from your answer and make SURE it is not more than 250 words.
"""

reviser_template = actor_reflection_prompt.partial(
    first_instruction=revise_instructions
)
reviser_responder = reviser_template | llm.bind_tools(
    tools=[ReviseAnswer],tool_choice="ReviseAnswer"
)



if __name__ == "__main__":
    human_message = HumanMessage(
        content="Write about AI-Powerd SOC / autonomous soc problem domain"
                "list startups that do that and raised capital"
    )
    chain = first_responder | pydantic_paser
    res = chain.invoke(input={"messages": [human_message]})
    print(res)











