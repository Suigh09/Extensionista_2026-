"""Filtros GLPI-like para listagens de projetos.

Cada linha de filtro é enviada como:
    field_i, op_i, value_i   (condição da linha i)
    combiner_i               (E/OU entre a linha i e a i+1)

Condições suportadas:
    exact        -> campo igual ao valor (iexact / booleano)
    not_exact    -> campo diferente do valor
    contains     -> campo contém o texto (icontains)
    not_contains -> campo não contém o texto
"""

from django.db.models import Q


def _values(request, name):
    """Valores repetidos de um mesmo parâmetro (ex.: ?status=1&status=2)."""
    raw = request.query_params.getlist(name)
    out = []
    for value in raw:
        for part in str(value).split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _row_filters(request, index):
    """Constrói o Q de uma linha de filtro pelo índice."""
    field = request.query_params.get(f"field_{index}")
    op = request.query_params.get(f"op_{index}", "contains")
    value = request.query_params.get(f"value_{index}")
    if field is None or value in (None, ""):
        return None

    q = _field_q(field, op, value, request)
    return q


def _field_q(field, op, value, request):
    negate = op in ("not_exact", "not_contains")
    exact = op in ("exact", "not_exact")

    if field == "q":
        # Texto livre: busca em nome, sobre e tema.
        base = Q()
        for word in str(value).split()[:20]:
            base |= (
                Q(name__icontains=word)
                | Q(about__icontains=word)
                | Q(theme_snapshot__title__icontains=word)
            )
        return ~base if negate else base

    if field == "status":
        base = Q(status__iexact=value)
    elif field == "showcase_status":
        base = Q(groups__showcase_entry__status__iexact=value)
    elif field == "is_active":
        base = Q(is_active=(value.lower() in ("true", "1", "sim", "yes")))
    elif field in ("advisor", "orientador"):
        base = _person_q("groups__responsible_professor__user", value, exact)
    elif field in ("evaluator", "avaliador"):
        base = _person_q("groups__evaluator__user", value, exact)
    elif field in ("student", "integrante", "aluno"):
        base = _person_q("groups__members__student__user", value, exact)
    elif field in ("leader", "lider"):
        base = _person_q("groups__leader__user", value, exact)
    elif field in ("room", "turma", "class_offering"):
        base = Q(class_offering__code__icontains=value) | Q(
            class_offering__subject__code__icontains=value
        )
        try:
            base |= Q(class_offering__pk=int(value))
        except (ValueError, TypeError):
            pass
    elif field in ("theme", "tema"):
        base = Q(theme_snapshot__title__icontains=value)
        try:
            base |= Q(theme__pk=int(value))
        except (ValueError, TypeError):
            pass
    else:
        return Q()  # campo desconhecido: sem filtro

    return ~base if negate else base


def _person_q(user_path, value, exact):
    """Busca pessoa por nome/username/RA, ou por pk quando numérico."""
    parts = str(value).split()
    q = Q()
    if exact and len(parts) == 1:
        token = parts[0]
        if token.isdigit():
            q = Q(**{f"{user_path}__pk": int(token)})
        else:
            q = Q(**{f"{user_path}__username__iexact": token})
    else:
        for word in parts:
            q &= (
                Q(**{f"{user_path}__first_name__icontains": word})
                | Q(**{f"{user_path}__last_name__icontains": word})
                | Q(**{f"{user_path}__username__icontains": word})
            )
    if "student" in user_path:
        # integrante também pode ser buscado por RA
        q |= Q(**{f"{user_path.replace('__user','')}__ra__icontains": value})
    return q


def apply_project_filters(queryset, request):
    """Aplica linhas de filtro GLPI-like sobre o queryset de projetos."""
    try:
        row_count = int(request.query_params.get("row_count", "0"))
    except (ValueError, TypeError):
        row_count = 0

    clauses = []
    combiners = []
    for i in range(row_count):
        q = _row_filters(request, i)
        if q is None:
            continue
        clauses.append(q)
        if i < row_count - 1:
            combiners.append(
                request.query_params.get(f"combiner_{i}", "and").strip().lower()
            )

    if not clauses:
        return queryset

    combined = clauses[0]
    for i, q in enumerate(clauses[1:]):
        if combiners[i] == "or":
            combined = combined | q
        else:
            combined = combined & q
    return queryset.filter(combined).distinct()
