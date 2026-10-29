"""Grounded facts, question scope and course references, independent of the LLM."""
import re
import unicodedata
from difflib import get_close_matches
from sqlalchemy import select
from .models import Message


def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


HEADINGS = {
    'descripcion': 'description', 'objetivos': 'objectives',
    'lugar de celebracion': 'place', 'lugar del evento': 'place',
    'comite organizador': None, 'instructores': None,
    'requisitos y detalles': None, 'materiales y equipos': 'materials',
    'contenidos': 'syllabus', 'fecha del curso': 'dates',
    'fechas de inscripciones': 'registration_dates', 'cupo de inscripciones': 'capacity',
    'horario': 'schedule', 'precio para los asistentes': 'price',
    'tipo de capacitacion': 'certificate', 'horas de capacitacion': 'duration',
    'beneficiarios': 'beneficiaries', 'modalidad': 'modality',
    'conocimientos previos': 'requirements',
}


def course_facts(course):
    blocks = {}
    current = None
    for raw in course.content.splitlines():
        line = raw.strip()
        if not line:
            continue
        label, sep, rest = line.partition(':')
        key = normalize(label).strip()
        if key in HEADINGS:
            current = HEADINGS[key]
            if current:
                blocks.setdefault(current, [])
                if sep and rest.strip():
                    blocks[current].append(rest.strip())
        elif re.match(r'^(clase|modulo|unidad)\s+\d+', normalize(line)):
            current = 'syllabus'
            blocks.setdefault(current, []).append(line)
        elif current:
            blocks[current].append(line)
    facts = {key: '\n'.join(lines).strip() for key, lines in blocks.items() if lines}
    # Importer headings for tab names precede their values; prerequisites themselves
    # are a single paragraph, followed by certification caveats and equipment.
    if facts.get('requirements'):
        facts['requirements'] = facts['requirements'].splitlines()[0]
    facts['duration'] = course.hours or facts.get('duration', '')
    facts['registration'] = course.registration_url
    return facts


def requested_fields(text):
    t = normalize(text)
    fields = []
    patterns = [
        ('description', r'de que (?:se )?trata|descripcion|en que consiste|que es|que (?:voy a )?aprend|hablame|resumen'),
        ('schedule', r'horario|a que hora|dias de clase'),
        ('price', r'precio|costo|cuesta|cuanto vale|valor|tarifa'),
        ('duration', r'duracion|cuanto dura|cuantas? horas'),
        ('requirements', r'requisit|conocimientos previos|necesito saber|desde cero'),
        ('syllabus', r'temario|pensum|contenidos|modulos|unidades'),
        ('objectives', r'objetivo'),
        ('modality', r'modalidad|presencial|virtual|en linea'),
        ('place', r'donde|ubicacion|lugar'),
        ('certificate', r'certificado|certificacion'),
    ]
    for name, pattern in patterns:
        if re.search(pattern, t):
            fields.append(name)
    date_question = re.search(r'fecha|cuando|que dia|inicia|inicio|empieza|comienza', t)
    enrollment = re.search(r'inscrip|inscrib|matricul|registr', t)
    if date_question:
        if enrollment:
            fields.append('registration_dates')
        if not enrollment or re.search(r'empieza|comienza|inicia|fecha del curso', t):
            fields.append('dates')
    if enrollment and not date_question:
        fields.append('registration')
    return list(dict.fromkeys(fields))


def scope_response(text):
    t = normalize(text)
    task = re.search(r'\b(escrib[ea](?:me)?|haz(?:me)?|genera(?:me)?|programame|crea(?:me)?|dame|resuelve|arregla|corrige|implementa|desarrolla|depura)\b.{0,90}\b(codigo|script|programa|funcion|algoritmo|ejercicio|tarea|receta|poema|chiste|cuento)\b', t)
    task = task or re.search(r'\b(puedes|podrias|quiero que|necesito que)\b.{0,35}\b(escribir|generar|programar|crear|hacer)\b.{0,40}\b(codigo|script|funcion|programa|ejercicio)\b', t)
    unrelated = re.search(r'\b(clima|pronostico del tiempo|capital de|resultado del partido|receta de)\b', t)
    if task or unrelated or re.match(r'^\s*(?:def \w+\(|import \w+|console\.log\()', t):
        return 'Puedo orientarte sobre los cursos del CTT-FISEI, sus requisitos, fechas e inscripción. No puedo resolver tareas ni escribir código por ti. Si buscas aprender a programar, puedo ayudarte a elegir un curso de Python.'
    return None


STOP = set('curso cursos de del el la las los un una unos unas y o en para por con sin que cual como cuanto cuando ese esa este esta anterior certificado certificacion certified preparacion programa fundamentos introduccion programacion basico basicos essential essentials certificate certified certification program associate entry level al desde cero me interesa quiero saber sobre informacion descripcion trata fecha horario precio tiene tienen es se puede'.split())
ALIASES = {'gitub': 'github', 'githab': 'github', 'git': 'github', 'phyton': 'python', 'pyton': 'python', 'piton': 'python', 'linuz': 'linux', 'arduno': 'arduino'}


def tokens(text):
    text = re.sub(r'git\s+hub', 'github', normalize(text))
    words = re.findall(r'[a-z0-9]+', text)
    levels = {'uno': '1', 'dos': '2', 'ii': '2'}
    return {ALIASES.get(w, levels.get(w, w)) for w in words if (len(w) >= 3 or w in ('1', '2', 'ii')) and w not in STOP}


def resolve_courses(db, lead, courses, text):
    """Return candidates plus whether a new course name was explicitly requested."""
    t = normalize(text)
    if lead.course_id and re.search(r'\b(?:curso anterior|el anterior)\b', t):
        history = db.scalars(select(Message).where(Message.lead_id == lead.id, Message.role == 'user').order_by(Message.id.desc()).limit(12)).all()
        for message in history:
            if scope_response(message.text):
                continue
            old = tokens(message.text)
            matches = [c for c in courses if ((tokens(c.title) & old) - {'1', '2'}) and (not old & {'1', '2'} or tokens(c.title) & old & {'1', '2'})]
            open_matches = [c for c in matches if c.status == 'ABIERTO']
            matches = open_matches or matches
            if len(matches) == 1 and matches[0].id != lead.course_id:
                return matches, True
        return [], False
    query = tokens(text)
    vocab = set().union(*(tokens(c.title) for c in courses)) if courses else set()
    # Fuzzy correction is confined to course vocabulary, never arbitrary substring matching.
    corrected = set(query)
    for word in query - vocab:
        if len(word) >= 5:
            match = get_close_matches(word, [v for v in vocab if len(v) >= 5], n=1, cutoff=0.86)
            if match:
                corrected.add(match[0])
    scored = []
    for course in courses:
        words = tokens(course.title)
        # A level alone is not sufficient to select a subject.
        overlap = (corrected & words) - {'1', '2'}
        if overlap:
            if corrected & {'1', '2'} and not (corrected & words & {'1', '2'}):
                continue
            scored.append((len(overlap) + 2*len(corrected & words & {'1', '2'}), course))
    if scored:
        maximum = max(score for score, _ in scored)
        matches = [c for score, c in scored if score == maximum]
        open_matches = [c for c in matches if c.status == 'ABIERTO']
        if open_matches:
            matches = open_matches
        if lead.course_id and not re.search(r'\b(otro|otros|cambiar)\b', t):
            selected = [c for c in matches if c.id == lead.course_id]
            if selected:
                return selected, True
        return matches, True
    explicit = re.search(r'\bcurso\s+(?:(?:de|sobre|llamado)\s+)?([a-z][a-z0-9]+)', t)
    if explicit and explicit.group(1) not in STOP and explicit.group(1) not in ('anterior', 'ese', 'este'):
        return [], True
    named = re.findall(r'\b[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+\b', text)
    ignored_names = STOP | {'uta', 'ctt', 'fisei', 'soy', 'estudiante', 'estudiantes', 'publico', 'general', 'puedo', 'puedes', 'necesito', 'gracias', 'hola'}
    if any(normalize(name) not in ignored_names and normalize(name) not in vocab for name in named[1:]):
        return [], True
    # The selected course survives follow-up questions, not a fresh unknown subject.
    if lead.course_id:
        return [c for c in courses if c.id == lead.course_id], False
    # Recover context from prior explicit user mentions, including after an advisor handover.
    history = db.scalars(select(Message).where(Message.lead_id == lead.id, Message.role == 'user').order_by(Message.id.desc()).limit(8)).all()
    for message in history:
        if message.text == text or scope_response(message.text):
            continue
        old_tokens = tokens(message.text)
        matches = [c for c in courses if (tokens(c.title) & old_tokens) - {'1', '2'}]
        if len(matches) == 1:
            return matches, False
        if matches:
            break
    return [], False


def choice_text(matches):
    return 'Encontré varias opciones. ¿A cuál te refieres?\n\n' + '\n'.join(f'• {c.title} — {c.hours} ({c.status})' for c in matches[:6])


LABELS = {'description': 'Descripción', 'dates': 'Fechas del curso', 'registration_dates': 'Inscripciones', 'schedule': 'Horario', 'price': 'Precios publicados', 'duration': 'Duración', 'requirements': 'Requisitos', 'syllabus': 'Temario', 'objectives': 'Objetivos', 'modality': 'Modalidad', 'place': 'Lugar', 'certificate': 'Certificado', 'registration': 'Inscripción'}


def answer_facts(course, fields):
    facts = course_facts(course)
    fields = fields or ['description']
    parts = []
    for field in fields:
        value = facts.get(field)
        if not value:
            parts.append(f'La ficha no publica {LABELS[field].lower()}. Un asesor puede confirmarlo.')
        elif field == 'description':
            parts.append(value[:1400])
        elif field == 'registration':
            parts.append(f'Puedes revisar el formulario oficial: {value}\nCompartir el enlace no confirma tu matrícula ni disponibilidad de cupos.')
        else:
            parts.append(f'{LABELS[field]}: {value[:1800]}')
    if course.status != 'ABIERTO':
        parts.append(f'Esta edición figura como {course.status.lower()}; no puedo confirmar una nueva convocatoria.')
    return f'{course.title}\n\n' + '\n\n'.join(parts) + f'\n\nFuente: {course.source_url}'
