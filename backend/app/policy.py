import re
from .agent import normalized

def policy_response(text):
    t = normalized(text)
    override = re.search(r'\b(ignora|ignorar|ignore|olvida|olvidar|forget|omite|revela|reveal|jailbreak)\b', t)
    target = re.search(r'\b(instrucciones|reglas|sistema|system|prompt|descuento|gratis|gratuito|clave|token|secreto|instructions)\b', t)
    impersonation = re.search(r'\b(soy el administrador|soy tu creador|modo desarrollador|developer mode)\b', t)
    if override and target or impersonation:
        return 'Puedo ayudarte con los cursos y las condiciones publicadas por el CTT-FISEI. No puedo autorizar gratuidad, descuentos ni cambios de políticas. ¿Qué curso te interesa revisar?'
    return None
