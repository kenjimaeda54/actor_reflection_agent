# Actor-Reflection Agent (LangGraph)

Agente de pesquisa que **responde, critica a própria resposta e sugere buscas** para melhorar — o padrão *Actor / Reflection* (base do "Reflexion"). A resposta não sai crua: passa por um ciclo de auto-crítica guiado pelo schema de saída.

## Estrutura

| Arquivo | Papel |
|---|---|
| `schemas.py` | Modelos Pydantic que definem o **formato obrigatório** da saída da LLM |
| `chains.py` | Prompt + LLM + parsers = primeira chain (o "Actor") |
| `.env` | Chave de API (não versionado) |

Modelo usado: `z-ai/glm-5.3-flash` via OpenRouter.

## Setup

```bash
uv sync                      # instala dependências
echo 'OPEN_ROUTER_API_KEY=...' >> .env
uv run chains.py             # roda o teste isolado do __main__
```

## Estado atual e próximos passos

- [x] Schema `AnswerQuestion` (resposta + reflexão + queries de busca)
- [x] Chain do primeiro respondente (Actor)
- [ ] Chain de **Reflection** (usa `Reflection` como schema de crítica)
- [ ] Grafo LangGraph: `Actor → Reflection → Revisor` em loop, com Tavily para executar as `search_queries`
- [ ] Nó de busca web (`langchain-tavily` já está nas dependências)

## Ciclo completo (para onde o projeto vai)

```
Pergunta → Actor (responde ~250 palavras)
        → Reflection (critica: o que falta / o que sobra)
        → Busca web com search_queries
        → Actor revisa com o novo material → repete até qualidade aceitável
```

---

# 📚 Notas de estudo — como pensar e fazer as coisas

> Seção de consulta futura. Todo o raciocínio que estava nos comentários do código foi movido para cá.

## 1. Ordem de raciocínio ao construir uma chain

```
Objetivo (ciclo de melhoria)
   ↓
Que dados preciso a cada volta?   → schema (schemas.py)
   ↓
Como garantir esse formato?       → bind_tools + tool_choice
   ↓
O que a model precisa saber?      → prompt (+ hora atual)
   ↓
Como reaproveitar o prompt?       → partial
   ↓
Funciona isolado?                 → chain de teste no __main__
```

Sempre comece pelo **schema**: ele é o contrato. Todo o resto (prompt, ferramentas, parser) existe para satisfazê-lo.

## 2. Schema Pydantic como contrato com a LLM

As `description` de cada `Field` são **enviadas à model como instrução** — elas dizem o que colocar em cada campo. Por isso são importantes: sem elas a model não sabe o que preencher. Escrevê-las bem é escrever prompt.

```python
answer: str = Field(description="~250 word detail answer to the question")
```

`Reflection` fica **dentro** de `AnswerQuestion` — assim a crítica é parte obrigatória da resposta, não um passo opcional que a model pode pular.

## 3. Forçando o formato: `bind_tools` + `tool_choice`

`bind_tools(tools=[AnswerQuestion])` diz à model: "você tem uma ferramenta chamada AnswerQuestion com este formato de argumentos". `tool_choice="AnswerQuestion"` **obriga** a chamá-la. Sem isso, ela poderia responder em texto livre e quebrar o parser.

## 4. Parsers: duas formas de ler a mesma saída

- `JsonOutputToolsParser(return_id=True)` — retorna dicts crus.
- `PydanticToolsParser(tools=[AnswerQuestion])` — pega os args e constrói objetos `AnswerQuestion` **validados**. Assim `res[0].answer` e `res[0].search_queries` funcionam como atributos, com validação de tipos. Preferível quando os dados vão alimentar o próximo passo do grafo.

## 5. Por que a hora atual no prompt?

A LLM não sabe que dia é hoje — ela só conhece o que viu no treino. Colocando `Current time: ...` no prompt, ela sabe a data atual, útil para pesquisa ("startups que levantaram capital em 2026").

## 6. `partial`: preenchendo variáveis antecipadamente

O prompt tem variáveis entre chaves: `{time}` e `{first_instruction}`. Normalmente você teria que passar todas no `invoke`. O `.partial(...)` preenche algumas antecipadamente, deixando só o resto para depois.

## 7. `lambda` no time — o detalhe que pega muita gente

```python
.partial(time=lambda: datetime.datetime.now().isoformat())
```

`time` usa lambda para ser **calculado a cada chamada**. Se fosse `time=datetime.now()` sem lambda, a hora seria fixada uma vez só, no momento em que o arquivo foi carregado.

## 8. Reaproveitando o template (camadas)

```python
first_responder_prompt_template = actor_reflection_prompt.partial(
    first_instruction="Provide a detailed ~250 word answer"
)
```

A Camada 2 reaproveita o template base e só preenche `first_instruction`. O mesmo esqueleto de prompt servirá para o nó de Reflection trocando só a instrução — é assim que o ciclo Actor/Reflection compartilha estrutura sem duplicar código.

## 9. Padrão de teste isolado

O bloco `if __name__ == "__main__":` roda a chain completa (prompt → LLM → parser) com uma pergunta real. Serve para validar o schema e o prompt **antes** de plugar no grafo do LangGraph — cada peça funciona isolada primeiro.
