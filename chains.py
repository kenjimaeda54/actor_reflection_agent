import os
import datetime

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputToolsParser, PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openrouter import ChatOpenRouter
from pydantic import SecretStr

from schemas import AnswerQuestion

load_dotenv()

APIKEY_OPENROUTER = os.environ.get("OPEN_ROUTER_API_KEY","")

llm = ChatOpenRouter(
    model="z-ai/glm-5.3-flash",
    api_key=SecretStr(APIKEY_OPENROUTER)
)
parser = JsonOutputToolsParser(return_id=True)

#PydanticToolsParser(tools=[AnswerQuestion]): pega os args e constrói objetos
# AnswerQuestion validados. Assim res[0].answer e res[0].search_queries funcionam como atributos, com validação de tipos.
parser_pydantic = PydanticToolsParser(tools=[AnswerQuestion])


#Por que o datetime? A LLM não sabe que dia é hoje. Ela só conhece
# o que viu no treino. Colocando Current time: ... no prompt, ela sabe a data atual,
# útil para pesquisa (“startups que levantaram capital em 2026”).

#Por que o partial? O prompt tem variáveis entre chaves: {time} e {first_instruction}.
# Normalmente você teria que passar todas no invoke. O partial preenche algumas variáveis antecipadamente,
# deixando só o resto para depois.
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
        ("system", "Answer the user's question above using the required format")
    ]
).partial(
    #time usa lambda para ser calculado a cada chamada.
    # Se fosse time=datetime.now() sem lambda, a hora seria fixada uma vez só,
    # no momento em que o arquivo foi carregado.
    time=lambda: datetime.datetime.now().isoformat()
)

# Camada 2: reaproveita o template base e preenche first_instruction
first_responder_prompt_template = actor_reflection_prompt.partial(
    first_instruction="Provide a detailed ~250 word answer"
)


#bind_tools(tools=[AnswerQuestion]) diz à model: “você tem uma ferramenta
# chamada AnswerQuestion com este formato de argumentos”.
#tool_choice="AnswerQuestion" obriga a model a chamar essa ferramenta.
# Sem isso, ela poderia responder em texto livre.
first_responder = first_responder_prompt_template | llm.bind_tools(
    tools=[AnswerQuestion],tool_choice="AnswerQuestion"
)

if __name__ == "__main__":
    human_message = HumanMessage(
        content="Write about AI-Powerd SOC / autonomous soc problem domain"
        "list startups that do that and raised capital"
    )
    chain = (
        first_responder_prompt_template
        | llm.bind_tools(tools=[AnswerQuestion], tool_choice="AnswerQuestion")
        | parser_pydantic
    )
    res = chain.invoke(input={"messages": [human_message] })
    print(res)


# Objetivo (ciclo de melhoria)
#    ↓
# Que dados preciso a cada volta?   → schema
#    ↓
# Como garantir esse formato?       → bind_tools + tool_choice
#    ↓
# O que a model precisa saber?      → prompt (+ time)
#    ↓
# Como reaproveitar o prompt?       → partial
#    ↓
# Funciona isolado?                 → chain de teste no __main__