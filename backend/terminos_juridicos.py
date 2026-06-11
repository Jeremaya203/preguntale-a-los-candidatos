"""
terminos_juridicos.py
─────────────────────────────────────────────────────────────────────────────
Diccionario de términos técnico-jurídicos y políticos relevantes para las
elecciones colombianas 2026. Usado por anotar_analyses.py para enriquecer
los análisis precalculados, y por el LLM como referencia en el system prompt.

Formato: { "término exacto": "Explicación en lenguaje ciudadano (máx 2 frases)" }

Las claves están en minúsculas. El script de anotación es case-insensitive.
─────────────────────────────────────────────────────────────────────────────
"""

TERMINOS = {

    # ── Mecanismos constitucionales ──────────────────────────────────────────
    "tutela": (
        "Mecanismo legal para proteger derechos fundamentales cuando están siendo violados. "
        "Es rápido: cualquier juez debe responder en 10 días."
    ),
    "acción de tutela": (
        "Mecanismo legal para proteger derechos fundamentales cuando están siendo violados. "
        "Es rápido: cualquier juez debe responder en 10 días."
    ),
    "habeas corpus": (
        "Derecho a exigir que un juez revise si tu detención es legal. "
        "Protege contra arrestos arbitrarios o sin fundamento."
    ),
    "acción popular": (
        "Mecanismo legal que puede usar cualquier ciudadano para defender derechos "
        "colectivos, como el medio ambiente o el espacio público."
    ),
    "acción de cumplimiento": (
        "Herramienta legal para obligar al Estado a cumplir una ley o acto "
        "administrativo que está incumpliendo."
    ),
    "derecho de petición": (
        "Derecho de todo ciudadano a hacerle preguntas o solicitudes al Estado, "
        "y a recibir respuesta en un plazo de 15 días hábiles."
    ),
    "referendo": (
        "Votación directa donde los ciudadanos aprueban o rechazan una ley "
        "o reforma constitucional propuesta."
    ),
    "referendo derogatorio": (
        "Votación para eliminar una ley ya existente. "
        "Los ciudadanos deciden si quieren que esa norma deje de aplicarse."
    ),
    "plebiscito": (
        "Consulta directa al pueblo sobre una decisión política importante del gobierno, "
        "como un acuerdo de paz o una política de Estado."
    ),
    "consulta popular": (
        "Mecanismo donde el gobierno pregunta a los ciudadanos sobre un tema "
        "específico, y el resultado es obligatorio si participa suficiente gente."
    ),
    "iniciativa legislativa popular": (
        "Derecho de los ciudadanos a proponer leyes directamente ante el Congreso "
        "cuando reúnen suficientes firmas."
    ),
    "revocatoria del mandato": (
        "Mecanismo para que los ciudadanos destituyan a un alcalde o gobernador "
        "antes de que termine su período, mediante una votación."
    ),
    "asamblea nacional constituyente": (
        "Cuerpo elegido por el pueblo para redactar o reformar la Constitución. "
        "Es la máxima expresión del poder del pueblo."
    ),
    "constituyente": (
        "Proceso o asamblea que crea o reescribe la Constitución de un país. "
        "Cambia las reglas fundamentales del juego político y jurídico."
    ),

    # ── Instituciones del Estado ─────────────────────────────────────────────
    "corte constitucional": (
        "El máximo tribunal que decide si las leyes respetan la Constitución. "
        "Si una ley viola derechos, la Corte la puede anular."
    ),
    "corte suprema de justicia": (
        "El tribunal más alto para casos penales y civiles en Colombia. "
        "Juzga a congresistas y ex presidentes."
    ),
    "consejo de estado": (
        "Tribunal que controla los actos del gobierno y la administración pública. "
        "Resuelve demandas contra el Estado."
    ),
    "fiscalía": (
        "Entidad encargada de investigar delitos y acusar a los criminales ante los jueces. "
        "Es la fiscalía general de la nación."
    ),
    "procuraduría": (
        "Entidad que vigila el comportamiento de los servidores públicos. "
        "Puede sancionarlos o retirarlos del cargo si actúan mal."
    ),
    "contraloría": (
        "Entidad que vigila cómo el Estado gasta el dinero público y detecta la corrupción. "
        "Puede declarar responsable fiscal a quien desperdicia o roba recursos."
    ),
    "defensoría del pueblo": (
        "Entidad que defiende los derechos humanos de los ciudadanos frente al Estado. "
        "Puede intervenir cuando el gobierno viola derechos."
    ),
    "registraduría": (
        "Entidad encargada de organizar las elecciones y llevar el registro civil "
        "(cédulas, nacimientos, matrimonios)."
    ),
    "consejo nacional electoral": (
        "Organismo que vigila las campañas políticas, la financiación de partidos "
        "y el cumplimiento de las reglas electorales."
    ),
    "cnc": (
        "Centro Nacional de Consultoría, una firma encuestadora colombiana registrada "
        "ante el Consejo Nacional Electoral."
    ),
    "uiaf": (
        "Unidad de Información y Análisis Financiero: entidad que detecta y reporta "
        "el lavado de dinero y la financiación del terrorismo."
    ),

    # ── Conceptos legales y constitucionales ────────────────────────────────
    "bloque de constitucionalidad": (
        "Conjunto de normas internacionales (tratados de derechos humanos) que tienen "
        "el mismo valor que la Constitución colombiana."
    ),
    "control de convencionalidad": (
        "Obligación de los jueces de revisar que las leyes colombianas cumplan con los "
        "tratados internacionales de derechos humanos que el país ha firmado."
    ),
    "control difuso": (
        "Facultad de cualquier juez (no solo la Corte Constitucional) para aplicar "
        "directamente la Constitución cuando una ley la contradice."
    ),
    "exequibilidad": (
        "Cuando la Corte Constitucional declara que una ley SÍ respeta la Constitución "
        "y por tanto puede aplicarse."
    ),
    "inexequibilidad": (
        "Cuando la Corte Constitucional declara que una ley viola la Constitución "
        "y la retira del ordenamiento jurídico."
    ),
    "nulidad electoral": (
        "Anulación de los resultados de una elección por irregularidades graves, "
        "como fraude o incumplimiento de las reglas."
    ),
    "fuero constitucional": (
        "Privilegio que tienen ciertos funcionarios (como el Presidente o congresistas) "
        "de ser juzgados solo por tribunales especiales, no por jueces ordinarios."
    ),
    "fuero penal militar": (
        "Sistema especial de justicia para los militares y policías, donde sus delitos "
        "son investigados por jueces militares, no civiles."
    ),
    "desafuero": (
        "Proceso para quitarle a un congresista su inmunidad especial y poder juzgarlo "
        "penalmente como cualquier ciudadano."
    ),
    "impedimento": (
        "Situación en que un juez, fiscal o funcionario debe apartarse de un caso "
        "porque tiene conflicto de intereses o relación con las partes."
    ),
    "recusación": (
        "Solicitud para apartar a un juez o funcionario de un caso porque se duda "
        "de su imparcialidad."
    ),
    "fallo de unificación": (
        "Decisión de un tribunal superior que se convierte en regla obligatoria "
        "para todos los jueces del país en casos similares."
    ),
    "precedente vinculante": (
        "Decisión judicial anterior que los jueces están obligados a seguir en casos "
        "parecidos. Garantiza que la ley se aplique igual para todos."
    ),
    "responsabilidad fiscal": (
        "Cuando la Contraloría determina que un funcionario causó daño al patrimonio "
        "público y debe devolverle el dinero al Estado."
    ),
    "pérdida de investidura": (
        "Sanción que le quita a un congresista su cargo de manera permanente "
        "por violaciones graves a las normas del Congreso."
    ),
    "moción de censura": (
        "Mecanismo del Congreso para retirar a un ministro de su cargo cuando "
        "considera que ha actuado mal."
    ),

    # ── Economía y política pública ──────────────────────────────────────────
    "sistema general de participaciones": (
        "El dinero que el gobierno nacional transfiere a los municipios y departamentos "
        "para financiar educación, salud y agua potable."
    ),
    "regalías": (
        "Dinero que le pagan al Estado las empresas que explotan recursos naturales "
        "(petróleo, carbón, oro) a cambio de ese derecho."
    ),
    "déficit fiscal": (
        "Cuando el gobierno gasta más de lo que recibe en impuestos. "
        "Obliga a endeudarse para cubrir la diferencia."
    ),
    "reforma tributaria": (
        "Cambio en las leyes de impuestos: quién paga más, quién paga menos, "
        "qué bienes o ingresos se gravan."
    ),
    "renta básica universal": (
        "Programa donde el Estado le da una suma fija de dinero a todos los ciudadanos, "
        "independientemente de si trabajan o no."
    ),
    "transferencias monetarias condicionadas": (
        "Subsidios que el Estado da a familias pobres, pero con la condición de que "
        "cumplan requisitos como llevar a los hijos al colegio o al médico."
    ),
    "sisbén": (
        "Sistema de información que clasifica a los colombianos según sus condiciones "
        "socioeconómicas para determinar quién puede recibir subsidios del Estado."
    ),
    "economía popular": (
        "El conjunto de actividades económicas de las personas de bajos ingresos: "
        "pequeños negocios, vendedores ambulantes, artesanos, agricultores familiares."
    ),
    "reforma agraria": (
        "Redistribución de la tierra rural, generalmente para darles acceso a campesinos "
        "que no la tienen, comprando o expropiando tierras ociosas o mal usadas."
    ),
    "catastro multipropósito": (
        "Actualización del registro de todos los predios del país con su valor real, "
        "quién los posee y cómo se usan, para cobrar impuestos justos y planificar el territorio."
    ),
    "fracking": (
        "Técnica para extraer petróleo o gas rompiendo las rocas del subsuelo con "
        "agua y químicos a presión. Es controversial por riesgos ambientales."
    ),
    "transición energética": (
        "Proceso de dejar de depender del petróleo y el carbón para usar cada vez más "
        "energías limpias como solar, eólica e hidráulica."
    ),
    "macrocorrupción": (
        "Corrupción organizada a gran escala donde redes de políticos, empresarios "
        "y funcionarios saquean el Estado de manera sistemática."
    ),
    "macrocorrupción sistémica": (
        "Corrupción tan profunda y extendida que captura instituciones enteras del Estado "
        "y se perpetúa a sí misma, como un sistema paralelo de poder."
    ),

    # ── Paz y conflicto ──────────────────────────────────────────────────────
    "paz total": (
        "Política del gobierno Petro para negociar simultáneamente con todos los grupos "
        "armados ilegales del país: guerrillas, paramilitares y bandas criminales."
    ),
    "acuerdo de paz": (
        "Pacto firmado en 2016 entre el gobierno colombiano y las FARC para terminar "
        "el conflicto armado. Incluye compromisos de tierras, política y justicia."
    ),
    "justicia transicional": (
        "Sistema especial de justicia para salir de un conflicto armado: busca verdad, "
        "reparación y reconciliación, con penas alternativas a la cárcel para quienes confiesen."
    ),
    "jep": (
        "Jurisdicción Especial para la Paz: tribunal creado para juzgar los crímenes "
        "del conflicto armado. Los que colaboren con la verdad tienen penas alternativas."
    ),
    "jurisdicción especial para la paz": (
        "Tribunal creado para juzgar los crímenes del conflicto armado. "
        "Los que colaboren con la verdad tienen penas alternativas a la cárcel."
    ),
    "sometimiento a la justicia": (
        "Proceso donde un grupo armado ilegal acepta entregarse, confesar sus crímenes "
        "y recibir penas reducidas a cambio de dejar las armas."
    ),
    "cese al fuego bilateral": (
        "Acuerdo temporal donde tanto el gobierno como un grupo armado dejan de atacarse, "
        "como paso previo a una negociación de paz."
    ),
    "desmovilización": (
        "Proceso por el cual los miembros de un grupo armado ilegal entregan sus armas "
        "y se reintegran a la vida civil."
    ),

    # ── Salud y seguridad social ─────────────────────────────────────────────
    "eps": (
        "Entidad Promotora de Salud: empresa intermediaria entre los ciudadanos y los "
        "hospitales en el sistema de salud colombiano."
    ),
    "ips": (
        "Institución Prestadora de Salud: clínicas, hospitales y centros médicos que "
        "atienden a los pacientes."
    ),
    "sistema general de seguridad social en salud": (
        "El conjunto de reglas, entidades y fondos que organizan la salud pública en "
        "Colombia. Incluye régimen contributivo (trabajadores) y subsidiado (pobres)."
    ),
    "régimen contributivo": (
        "Sistema de salud para trabajadores y sus familias, que pagan una cotización "
        "mensual basada en su salario."
    ),
    "régimen subsidiado": (
        "Sistema de salud gratuito para personas sin capacidad de pago, financiado "
        "con recursos del Estado."
    ),
    "colpensiones": (
        "Fondo estatal de pensiones en Colombia. Administra las pensiones de los "
        "trabajadores que cotizan al sistema público."
    ),
    "afp": (
        "Administradora de Fondos de Pensiones: empresa privada que administra los "
        "ahorros pensionales de los trabajadores."
    ),
    "prima media": (
        "Sistema de pensión pública donde todos los cotizantes aportan a un fondo común "
        "y el Estado garantiza una pensión mínima."
    ),
    "ahorro individual": (
        "Sistema de pensión privado donde cada trabajador ahorra en su propia cuenta "
        "y su pensión depende de lo que haya acumulado."
    ),

    # ── Términos electorales ─────────────────────────────────────────────────
    "segunda vuelta": (
        "Segunda ronda de votaciones cuando ningún candidato obtiene más del 50% "
        "en la primera vuelta. Solo compiten los dos más votados."
    ),
    "balotaje": (
        "Segunda vuelta electoral. Los dos candidatos con más votos compiten "
        "directamente para ver cuál obtiene la mayoría."
    ),
    "tarjetón": (
        "La papeleta de votación en Colombia. Lista todos los candidatos "
        "y el ciudadano marca su voto."
    ),
    "umbral electoral": (
        "Porcentaje mínimo de votos que necesita un partido para mantener "
        "su personería jurídica o acceder a curules en el Congreso."
    ),
    "personería jurídica": (
        "Reconocimiento legal de un partido político para existir, inscribir "
        "candidatos y recibir recursos del Estado."
    ),
    "curul": (
        "Escaño o puesto en el Congreso (Senado o Cámara de Representantes). "
        "Cada curul representa a un congresista electo."
    ),
    "circunscripción": (
        "División territorial para efectos electorales que determina cuántos "
        "representantes elige cada región."
    ),
    "voto en blanco": (
        "Opción de no apoyar a ningún candidato. Si el voto en blanco gana, "
        "se repiten las elecciones sin los mismos candidatos."
    ),
    "escrutinio": (
        "Proceso oficial de conteo y verificación de votos realizado por jueces "
        "y funcionarios. Es el resultado legal, diferente al preconteo."
    ),
    "preconteo": (
        "Conteo rápido e informativo que hace la Registraduría la noche de las "
        "elecciones. No es el resultado oficial, pero suele ser muy preciso."
    ),
    "grupo significativo de ciudadanos": (
        "Forma de inscribir un candidato sin pertenecer a un partido político, "
        "recogiendo firmas de ciudadanos que lo respalden."
    ),
    "consulta interpartidista": (
        "Elección interna donde los votantes de varios partidos aliados "
        "eligen a un candidato único para las elecciones generales."
    ),
    "aval": (
        "Certificado oficial que un partido político le da a un candidato "
        "para que pueda inscribirse a unas elecciones con ese partido."
    ),

    # ── Términos de desinformación y medios ──────────────────────────────────
    "bodega": (
        "En Colombia, se llama 'bodega' a una red coordinada de personas que "
        "difunden propaganda o desinformación en redes sociales a favor de alguien."
    ),
    "chuzadas": (
        "Interceptaciones ilegales de comunicaciones (teléfonos, correos). "
        "Escándalo del DAS en el gobierno Uribe donde se espiaba a opositores y periodistas."
    ),
    "parapolítica": (
        "Escándalo donde se documentaron vínculos entre congresistas colombianos "
        "y grupos paramilitares ilegales."
    ),
    "farcpolítica": (
        "Acusación de vínculos entre políticos colombianos, especialmente de izquierda, "
        "y las FARC. Ha sido usada frecuentemente como ataque político."
    ),

    # ── Otros términos relevantes ────────────────────────────────────────────
    "estado de derecho": (
        "Sistema donde tanto los ciudadanos como el gobierno están obligados a cumplir "
        "la ley. Nadie está por encima de la Constitución."
    ),
    "separación de poderes": (
        "Principio que divide el poder del Estado en tres ramas independientes: "
        "ejecutivo (gobierno), legislativo (Congreso) y judicial (jueces)."
    ),
    "estado social de derecho": (
        "Modelo de Estado definido en la Constitución de 1991 donde el gobierno "
        "tiene la obligación de garantizar derechos sociales como salud, educación y vivienda."
    ),
    "checks and balances": (
        "Sistema de frenos y contrapesos donde cada rama del poder controla a las otras "
        "para evitar que alguna acumule demasiado poder."
    ),
    "pnd": (
        "Plan Nacional de Desarrollo: documento que define las metas y prioridades "
        "del gobierno durante sus cuatro años de mandato."
    ),
    "plan nacional de desarrollo": (
        "Documento que define las metas y prioridades del gobierno durante sus "
        "cuatro años de mandato. Tiene fuerza de ley."
    ),
    "decreto ley": (
        "Norma con fuerza de ley que dicta el Presidente sin pasar por el Congreso, "
        "usando facultades especiales que le da la Constitución."
    ),
    "estado de emergencia económica": (
        "Declaración presidencial que permite al gobierno tomar medidas extraordinarias "
        "ante una crisis económica grave, sin pasar por el Congreso."
    ),
    "estado de conmoción interior": (
        "Declaración presidencial ante una grave amenaza al orden público que permite "
        "suspender temporalmente algunas garantías ciudadanas."
    ),
}


def get_terminos_para_prompt() -> str:
    """
    Retorna una representación del diccionario para incluir en el system prompt del LLM.
    Solo incluye los 40 términos más relevantes para no sobrecargar el contexto.
    """
    prioritarios = [
        "tutela", "acción de tutela", "habeas corpus", "referendo", "plebiscito",
        "consulta popular", "asamblea nacional constituyente", "constituyente",
        "corte constitucional", "fiscalía", "procuraduría", "contraloría",
        "bloque de constitucionalidad", "nulidad electoral", "fuero constitucional",
        "desafuero", "moción de censura", "sistema general de participaciones",
        "regalías", "déficit fiscal", "reforma tributaria", "renta básica universal",
        "sisbén", "reforma agraria", "catastro multipropósito", "fracking",
        "transición energética", "macrocorrupción", "macrocorrupción sistémica",
        "paz total", "jep", "justicia transicional", "desmovilización",
        "eps", "colpensiones", "segunda vuelta", "balotaje", "escrutinio",
        "preconteo", "bodega",
    ]
    lines = ["DICCIONARIO DE REFERENCIA (usa estas explicaciones exactas):"]
    for t in prioritarios:
        if t in TERMINOS:
            lines.append(f'  "{t}": "{TERMINOS[t]}"')
    return "\n".join(lines)


if __name__ == "__main__":
    print(f"Total de términos en el diccionario: {len(TERMINOS)}")
    print("\nEjemplos:")
    for k, v in list(TERMINOS.items())[:5]:
        print(f"  [{k}]: {v[:80]}...")
