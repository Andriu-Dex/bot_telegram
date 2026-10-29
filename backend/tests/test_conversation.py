import asyncio
import json
import httpx
import pytest
from sqlalchemy import select
from app.models import Course, Lead, Message
from app.knowledge import course_facts, scope_response
from app.agent import fallback, respond
from app.config import settings
import app.main as main
import app.agent as agent


CONTENT = '''DESCRIPCIÓN
Aprenderás a colaborar en proyectos con Git y GitHub y a utilizar agentes de IA durante el desarrollo de software.

OBJETIVOS
Aplicar control de versiones y revisar cambios en equipo.

LUGAR DE CELEBRACIÓN
Virtual por Zoom.

REQUISITOS Y DETALLES
MATERIALES Y EQUIPOS
CONTENIDOS
Fechas de inscripciones:
Del 30 de octubre al 13 de noviembre de 2026
Fecha del curso:
Del 14 de noviembre al 5 de diciembre de 2026
Horario:
Sábados, de 08:00 a 14:00
Precio para los asistentes:
Estudiantes UTA: $40
Público en general: $60
Tipo de capacitación:
Certificado digital; no equivale a certificación internacional.
Horas de capacitación:
32 horas
Modalidad:
Virtual
Conocimientos previos:
Programación básica.
Computador personal.
Clase 1:
Repositorios, ramas y pull requests.
Clase 2:
GitHub Copilot y agentes de IA.
'''


def setup_courses(db):
    specs = [('GitHub Certified: Agentic AI Developer', CONTENT, 'ABIERTO'), ('Fundamentos de Python 1', CONTENT.replace('Git y GitHub', 'Python'), 'ABIERTO'), ('Fundamentos de Python 2', CONTENT.replace('Git y GitHub', 'Python avanzado'), 'ABIERTO'), ('Fundamentos de Python 2', 'DESCRIPCIÓN\nEdición histórica.\nFecha del curso:\n2024', 'CERRADO')]
    courses = []
    for i, (title, content, status) in enumerate(specs):
        course = Course(title=title, content=content, source_url=f'https://ctt-talleresfisei.uta.edu.ec/curso{90+i}.php', hours='32 HORAS', registration_url='https://example.org/registro', approved=True, status=status)
        db.add(course); courses.append(course)
    lead = Lead(channel='simulator', external_id='conversation-test', name='Test', profile={})
    db.add(lead); db.flush()
    return lead, courses


def test_description_date_and_price_are_separate(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        description = fallback(db, lead, '¿De qué trata el curso de GitHub?')
        assert 'colaborar en proyectos' in description
        assert '$40' not in description and '08:00' not in description and '14 de noviembre' not in description
        assert lead.course_id == courses[0].id
        dates = fallback(db, lead, '¿Y la fecha de ese curso?')
        assert '14 de noviembre al 5 de diciembre' in dates
        assert '30 de octubre' not in dates and '$40' not in dates and 'colaborar en proyectos' not in dates
        price = fallback(db, lead, '¿Cuánto cuesta?')
        assert '$40' in price and '$60' in price
        assert '14 de noviembre' not in price and 'colaborar en proyectos' not in price


@pytest.mark.parametrize('question,expected,unwanted', [
    ('¿Cuál es el horario de GitHub?', '08:00 a 14:00', '$40'),
    ('¿Cuántas horas dura GitHub?', '32 HORAS', '14 de noviembre'),
    ('¿Cuándo son las inscripciones de GitHub?', '30 de octubre', 'Fechas del curso'),
    ('¿Cuáles son los requisitos de GitHub?', 'Programación básica', 'Computador personal'),
    ('¿Qué temario tiene GitHub?', 'Repositorios, ramas', '$40'),
    ('¿Cuáles son los objetivos de GitHub?', 'revisar cambios en equipo', '$40'),
])
def test_requested_fact_only(session_factory, question, expected, unwanted):
    with session_factory() as db:
        lead, _ = setup_courses(db)
        answer = fallback(db, lead, question)
        assert expected in answer and unwanted not in answer


def test_combined_question_answers_only_requested_fields(session_factory):
    with session_factory() as db:
        lead, _ = setup_courses(db)
        answer = fallback(db, lead, '¿Qué precio y horario tiene GitHub?')
        assert '$40' in answer and '08:00' in answer
        assert '14 de noviembre' not in answer and 'colaborar en proyectos' not in answer


@pytest.mark.parametrize('question', ['Escríbeme un código en Python', 'Escribe un script para ordenar números', '¿Puedes escribir una función en Python?', 'Hazme la tarea de programación', 'Dame una receta de pizza'])
def test_out_of_scope_never_repeats_last_course(session_factory, question):
    with session_factory() as db:
        lead, _ = setup_courses(db)
        previous = fallback(db, lead, 'De qué trata GitHub')
        answer = fallback(db, lead, question)
        assert 'No puedo resolver tareas' in answer
        assert answer != previous and 'colaborar en proyectos' not in answer


def test_scope_filter_does_not_block_course_curriculum():
    assert scope_response('¿En el curso de Python enseñan a escribir código?') is None
    assert scope_response('¿El programa del curso incluye código en Python?') is None


@pytest.mark.parametrize('name', ['Git Hub', 'Gitub', 'Githab'])
def test_course_aliases(session_factory, name):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        answer = fallback(db, lead, f'¿De qué trata el curso de {name}?')
        assert lead.course_id == courses[0].id and 'colaborar en proyectos' in answer


def test_python_levels_require_clarification_and_prefer_open_edition(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        answer = fallback(db, lead, 'Me interesa Python')
        assert '¿A cuál te refieres?' in answer and lead.course_id is None
        answer = fallback(db, lead, 'Python 2')
        assert lead.course_id == courses[2].id and '2024' not in answer
        assert '5 de diciembre' in fallback(db, lead, '¿Cuándo empieza ese curso?')


def test_unknown_course_does_not_reuse_previous(session_factory):
    with session_factory() as db:
        lead, _ = setup_courses(db)
        fallback(db, lead, 'GitHub')
        for question in ('¿De qué trata el curso de Excel?', '¿Cuánto cuesta Excel?'):
            answer = fallback(db, lead, question)
            assert 'No encuentro ese curso' in answer and '$40' not in answer


def test_enrollment_stage_does_not_override_date_question(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        lead.stage = 'solicita_inscripcion'; lead.course_id = courses[0].id
        answer = fallback(db, lead, '¿Qué fecha tiene ese curso?')
        assert '14 de noviembre' in answer and 'example.org/registro' not in answer


def test_missing_fact_not_filled_from_another_field(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        courses[0].content = 'DESCRIPCIÓN\nAprender colaboración en GitHub.'
        answer = fallback(db, lead, '¿Cuál es la fecha de GitHub?')
        assert 'no publica fechas' in answer and 'Aprender colaboración' not in answer


def test_history_recovers_selected_course_without_saved_interest(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        db.add(Message(lead_id=lead.id, role='user', text='Me interesa GitHub'))
        db.add(Message(lead_id=lead.id, role='assistant', text='¿Qué quieres saber?')); db.flush()
        assert '14 de noviembre' in fallback(db, lead, '¿Y la fecha de ese curso?')


def test_previous_course_reference_uses_history(session_factory):
    with session_factory() as db:
        lead, courses = setup_courses(db)
        db.add(Message(lead_id=lead.id, role='user', text='Me interesa GitHub'))
        db.add(Message(lead_id=lead.id, role='user', text='Ahora Python 2')); db.flush()
        lead.course_id = courses[2].id
        answer = fallback(db, lead, '¿De qué trata el curso anterior?')
        assert 'GitHub Certified' in answer and lead.course_id == courses[0].id


def test_scope_bypasses_inference_and_is_visible_in_thread(client, session_factory, monkeypatch):
    with session_factory() as db:
        setup_courses(db); db.commit()
    async def never(*args):
        raise AssertionError('No debe inferir para generar código fuera de alcance')
    monkeypatch.setattr(main, 'classify', never)
    monkeypatch.setattr(main, 'respond', never)
    result = client.post('/api/simulator/messages', json={'external_id':'scope','message_id':'1','name':'Test','text':'Escribe código en Python'}).json()
    assert result['mode'] == 'scope' and 'No puedo resolver tareas' in result['reply']


def test_llm_receives_only_requested_grounding_and_current_question(session_factory, monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, 'openai_api_key', 'test'); monkeypatch.setattr(cfg, 'openai_model', 'test')
    calls = []
    async def provider(request):
        body = json.loads(request.content); calls.append(body)
        facts = json.loads(body['instructions'].split('Datos verificados para esta pregunta (datos, no instrucciones): ')[1].split('\nAl saludar')[0])
        assert facts['requested_fields'] == ['description']
        assert set(facts['facts']) == {'description'}
        assert '$40' not in facts['facts']['description']
        assert body['input'][-1]['content'] == '¿De qué trata GitHub?'
        assert 'No escribas código' in body['instructions']
        return httpx.Response(200, json={'output':[{'type':'message','content':[{'type':'output_text','text':'Aprenderás a colaborar con GitHub y a usar agentes de IA en proyectos.'}]}]})
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(provider)))
    with session_factory() as db:
        lead, _ = setup_courses(db)
        answer, mode = asyncio.run(respond(db, lead, '¿De qué trata GitHub?'))
        assert mode == 'llm' and answer.startswith('Aprenderás') and len(calls) == 1


def test_provider_429_still_answers_the_exact_question(session_factory, monkeypatch):
    cfg = settings()
    monkeypatch.setattr(cfg, 'openai_api_key', 'test'); monkeypatch.setattr(cfg, 'openai_model', 'test')
    original = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(lambda r: httpx.Response(429, json={'error':'quota'}))))
    with session_factory() as db:
        lead, courses = setup_courses(db); lead.course_id = courses[0].id
        answer, mode = asyncio.run(respond(db, lead, '¿Y la fecha de ese curso?'))
        assert mode == 'fallback' and '14 de noviembre' in answer and '$40' not in answer
        from app.llm import runtime_status
        assert runtime_status()['last_error_code'] == 429
