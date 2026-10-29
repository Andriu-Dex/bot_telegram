"""Provider boundary. Gemini preserves complete native content/thought signatures."""
import json
from datetime import datetime, timezone
import httpx
from google import genai
from google.genai import types, errors
from .network import tls_context

ProviderError = errors.APIError
_runtime = {'successful_calls': 0, 'failed_calls': 0, 'last_success_at': None, 'last_failure_at': None, 'last_error_code': None, 'last_error_type': None}

def runtime_status():
    return dict(_runtime)

class Conversation:
    def __init__(self, cfg, instructions, history, tools=None, schema=None, max_tokens=3072, timeout=30):
        self.cfg, self.instructions = cfg, instructions
        self.tools, self.schema, self.max_tokens = tools or [], schema, max_tokens
        self.inputs = list(history)
        self.pending = []
        self.google = None
        self.http = None
        if cfg.ai_provider_id == 'gemini':
            base = cfg.ai_provider_base_url or 'https://generativelanguage.googleapis.com/v1beta'
            # Accept the user's OpenAI-compatibility base while using native Gemini.
            base = base.rstrip('/').removesuffix('/openai').removesuffix('/v1beta').removesuffix('/v1')
            self.google = genai.Client(api_key=cfg.llm_key, http_options=types.HttpOptions(base_url=base, api_version='v1beta', timeout=timeout*1000, retry_options=types.HttpRetryOptions(attempts=1), async_client_args={'verify': tls_context()}))
            self.contents = [types.Content(role='model' if m['role']=='assistant' else 'user', parts=[types.Part(text=m['content'])]) for m in history]
        elif cfg.ai_provider_id != 'openai':
            raise ValueError('Proveedor de IA no soportado')

    async def __aenter__(self):
        if not self.google:
            self.http = httpx.AsyncClient(timeout=40, verify=tls_context())
        return self

    async def __aexit__(self, *_):
        if self.google:
            await self.google.aio.aclose()
        if self.http:
            await self.http.aclose()

    async def generate(self):
        try:
            output = await self._generate()
            if not output:
                raise ValueError('El proveedor no devolvió una respuesta visible ni herramientas')
        except (httpx.HTTPError, ProviderError, ValueError, KeyError, TypeError) as exc:
            code = getattr(exc, 'code', None) or (exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None)
            _runtime.update(failed_calls=_runtime['failed_calls'] + 1, last_failure_at=datetime.now(timezone.utc).isoformat(), last_error_code=code, last_error_type=type(exc).__name__)
            raise
        _runtime.update(successful_calls=_runtime['successful_calls'] + 1, last_success_at=datetime.now(timezone.utc).isoformat())
        return output

    async def _generate(self):
        if not self.google:
            body = {'model': self.cfg.llm_model, 'instructions': self.instructions, 'input': self.inputs, 'max_output_tokens': self.max_tokens, 'store': False}
            if self.tools:
                body['tools'] = self.tools
            if self.schema:
                body['text'] = {'format': {'type': 'json_schema', 'name': 'triage', 'strict': True, 'schema': self.schema}}
            base = self.cfg.ai_provider_base_url or self.cfg.openai_base_url
            response = await self.http.post(base.rstrip('/')+'/responses', headers={'Authorization': f'Bearer {self.cfg.llm_key}'}, json=body)
            response.raise_for_status()
            output = response.json()['output']
            self.inputs.extend(output)
            return output
        if self.pending:
            self.contents.append(types.Content(role='user', parts=self.pending))
            self.pending = []
        config = {'system_instruction': self.instructions, 'max_output_tokens': self.max_tokens}
        if self.cfg.llm_model.removeprefix('models/') == 'gemini-3.8-flash':
            # This model supports low/medium/high; minimal is explicitly unsupported.
            config['thinking_config'] = types.ThinkingConfig(thinking_level='low')
        if self.tools:
            config['tools'] = [types.Tool(function_declarations=[types.FunctionDeclaration(name=t['name'], description=t['description'], parameters_json_schema=t['parameters']) for t in self.tools])]
            config['automatic_function_calling'] = types.AutomaticFunctionCallingConfig(disable=True)
        if self.schema:
            config['response_mime_type'] = 'application/json'
            config['response_json_schema'] = self.schema
        response = await self.google.aio.models.generate_content(model=self.cfg.llm_model, contents=self.contents, config=types.GenerateContentConfig(**config))
        if not response.candidates or not response.candidates[0].content:
            raise ValueError('Gemini no devolvió contenido')
        if str(getattr(response.candidates[0], 'finish_reason', '')) in ('FinishReason.MAX_TOKENS', 'MAX_TOKENS'):
            raise ValueError('Gemini agotó los tokens antes de completar la respuesta')
        content = response.candidates[0].content
        self.contents.append(content)
        output = []
        for part in content.parts or []:
            if part.function_call:
                call = part.function_call
                output.append({'type': 'function_call', 'name': call.name, 'arguments': json.dumps(call.args or {}), 'call_id': call.id or '', 'native_id': call.id})
            elif part.text and not part.thought:
                output.append({'type': 'message', 'content': [{'type': 'output_text', 'text': part.text}]})
        return output

    def tool_result(self, call, value):
        if self.google:
            self.pending.append(types.Part(function_response=types.FunctionResponse(name=call['name'], id=call.get('native_id'), response={'result': value})))
        else:
            self.inputs.append({'type': 'function_call_output', 'call_id': call['call_id'], 'output': json.dumps(value, ensure_ascii=False)})

def output_text(output):
    return '\n'.join(p['text'] for o in output if o['type']=='message' for p in o.get('content',[]) if p['type']=='output_text')
