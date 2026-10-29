import asyncio
from types import SimpleNamespace
from google.genai import types
from app.llm import Conversation, output_text
import app.llm as llm

def config():
    return SimpleNamespace(ai_provider_id='gemini',llm_key='test',llm_model='gemini-test',ai_provider_base_url='https://generativelanguage.googleapis.com/v1beta/openai')

def test_gemini_preserves_signatures_and_tool_result_ids(monkeypatch):
    requests=[]
    native=types.Content(role='model',parts=[types.Part(function_call=types.FunctionCall(name='consultar_cursos',args={},id='call-1'),thought_signature=b'opaque-signature')])
    async def generate(**kwargs):
        requests.append({'contents':list(kwargs['contents']),'config':kwargs['config']})
        return SimpleNamespace(candidates=[SimpleNamespace(content=native if len(requests)==1 else types.Content(role='model',parts=[types.Part(text='Respuesta del catálogo')]))])
    async def close():pass
    def client(**kwargs):
        assert kwargs['http_options'].base_url=='https://generativelanguage.googleapis.com'
        assert kwargs['http_options'].retry_options.attempts==1
        return SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate),aclose=close))
    monkeypatch.setattr(llm.genai,'Client',client)
    async def scenario():
        tools=[{'name':'consultar_cursos','description':'Catálogo aprobado','parameters':{'type':'object','properties':{},'required':[],'additionalProperties':False}}]
        async with Conversation(config(),'Solo cursos aprobados',[{'role':'user','content':'Ver cursos'}],tools) as conversation:
            calls=await conversation.generate()
            conversation.tool_result(calls[0],[{'id':1,'title':'GitHub'}])
            assert output_text(await conversation.generate())=='Respuesta del catálogo'
        assert requests[1]['contents'][-2] is native
        assert requests[1]['contents'][-2].parts[0].thought_signature==b'opaque-signature'
        assert requests[1]['contents'][-1].parts[0].function_response.id=='call-1'
    asyncio.run(scenario())

def test_gemini_structured_classifier_schema(monkeypatch):
    schema={'type':'object','properties':{'state':{'type':'string','enum':['interesado','dudoso']}},'required':['state']}
    async def generate(**kwargs):
        assert kwargs['config'].response_mime_type=='application/json'
        assert kwargs['config'].response_json_schema==schema
        return SimpleNamespace(candidates=[SimpleNamespace(content=types.Content(role='model',parts=[types.Part(text='{"state":"dudoso"}')]))])
    async def close():pass
    monkeypatch.setattr(llm.genai,'Client',lambda **kw:SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate),aclose=close)))
    async def scenario():
        async with Conversation(config(),'Clasifica significado',[{'role':'user','content':'Me parece caro'}],schema=schema) as conversation:
            assert 'dudoso' in output_text(await conversation.generate())
    asyncio.run(scenario())

def test_gemini_38_uses_supported_low_thinking_and_rejects_truncation(monkeypatch):
    import pytest
    async def generate(**kwargs):
        assert kwargs['config'].thinking_config.thinking_level.value == 'LOW'
        return SimpleNamespace(candidates=[SimpleNamespace(finish_reason='MAX_TOKENS', content=types.Content(role='model',parts=[types.Part(text='Respuesta incompleta')]))])
    async def close():pass
    monkeypatch.setattr(llm.genai,'Client',lambda **kw:SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate),aclose=close)))
    async def scenario():
        cfg=config();cfg.llm_model='gemini-3.8-flash'
        async with Conversation(cfg,'Responde brevemente',[{'role':'user','content':'Fecha del curso'}]) as conversation:
            with pytest.raises(ValueError,match='agotó los tokens'):
                await conversation.generate()
    asyncio.run(scenario())
