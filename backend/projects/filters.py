"""Filtros GLPI-like para listagens de projetos."""

from django.db.models import Q


def _values(request, *names):
    result = []
    for name in names:
        for value in request.query_params.getlist(name):
            for part in str(value).split(","):
                part = part.strip()
                if part:
                    result.append(part)
    # preserve order, drop duplicates
    seen = set()
    unique = []
    for item in result:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _bool(value):
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in {"true", "1", "yes", "sim"}:
        return True
    if lowered in {"false", "0", "no", "nao", "não"}:
        return False
    return None


def apply_project_filters(queryset, request):
    combine = (request.query_params.get("combine") or "and").strip().lower()
    use_or = combine == "or"

    criteria = []

    # Texto livre (nome, sobre, grupo, integrantes, orientador, avaliador, tema)
    words = []
    for raw in _values(request, "q", "search"):
        words.extend(raw.split())
    if words:
        text_q = Q()
        for word in words[:20]:
            text_q |= (
                Q(name__icontains=word)
                | Q(about__icontains=word)
                | Q(groups__name__icontains=word)
                | Q(groups__members__student__user__first_name__icontains=word)
                | Q(groups__members__student__user__last_name__icontains=word)
                | Q(groups__members__student__ra__icontains=word)
                | Q(groups__responsible_professor__user__first_name__icontains=word)
                | Q(groups__responsible_professor__user__last_name__icontains=word)
                | Q(groups__evaluator__user__first_name__icontains=word)
                | Q(groups__evaluator__user__last_name__icontains=word)
                | Q(theme_snapshot__title__icontains=word)
            )
        criteria.append(text_q)

    # Status
    statuses = _values(request, "status")
    if statuses:
        criteria.append(Q(status__in=statuses))

    # Orientador (id ou fragmento de nome)
    advisors = _values(request, "advisor", "orientador")
    if advisors:
        adv_q = Q()
        for value in advisors:
            if value.isdigit():
                adv_q |= Q(groups__responsible_professor__pk=int(value))
            adv_q |= Q(groups__responsible_professor__user__first_name__icontains=value)
            adv_q |= Q(groups__responsible_professor__user__last_name__icontains=value)
            adv_q |= Q(groups__responsible_professor__user__username__icontains=value)
        criteria.append(adv_q)

    # Avaliador
    evaluators = _values(request, "evaluator", "avaliador")
    if evaluators:
        ev_q = Q()
        for value in evaluators:
            if value.isdigit():
                ev_q |= Q(groups__evaluator__pk=int(value))
            ev_q |= Q(groups__evaluator__user__first_name__icontains=value)
            ev_q |= Q(groups__evaluator__user__last_name__icontains=value)
            ev_q |= Q(groups__evaluator__user__username__icontains=value)
        criteria.append(ev_q)

    # Integrante (aluno)
    students = _values(request, "student", "integrante", "aluno")
    if students:
        st_q = Q()
        for value in students:
            if value.isdigit():
                st_q |= Q(groups__members__student__pk=int(value))
            st_q |= Q(groups__members__student__user__first_name__icontains=value)
            st_q |= Q(groups__members__student__user__last_name__icontains=value)
            st_q |= Q(groups__members__student__ra__icontains=value)
            st_q |= Q(groups__members__student__user__username__icontains=value)
        criteria.append(st_q)

    # Líder
    leaders = _values(request, "leader", "lider")
    if leaders:
        ld_q = Q()
        for value in leaders:
            if value.isdigit():
                ld_q |= Q(groups__leader__pk=int(value))
            ld_q |= Q(groups__leader__user__first_name__icontains=value)
            ld_q |= Q(groups__leader__user__last_name__icontains=value)
            ld_q |= Q(groups__leader__ra__icontains=value)
            ld_q |= Q(groups__leader__user__username__icontains=value)
        criteria.append(ld_q)

    # Turma / sala acadêmica
    rooms = _values(request, "room", "turma", "class_offering")
    if rooms:
        rm_q = Q()
        for value in rooms:
            rm_q |= Q(class_offering__code__icontains=value)
            rm_q |= Q(class_offering__subject__code__icontains=value)
            try:
                rm_q |= Q(class_offering__pk=int(value))
            except (ValueError, TypeError):
                pass
        criteria.append(rm_q)

    # Tema
    themes = _values(request, "theme", "tema")
    if themes:
        th_q = Q()
        for value in themes:
            th_q |= Q(theme_snapshot__title__icontains=value)
            try:
                th_q |= Q(theme__pk=value)
            except (ValueError, TypeError):
                pass
        criteria.append(th_q)

    # Ativo/inativo
    active = _bool(request.query_params.get("is_active"))
    if active is not None:
        criteria.append(Q(is_active=active))

    # Status da agenda da Mostra
    showcase_statuses = _values(request, "showcase_status", "agenda_status")
    if showcase_statuses:
        criteria.append(Q(groups__showcase_entry__status__in=showcase_statuses))

    if not criteria:
        return queryset

    combined = criteria[0]
    for q in criteria[1:]:
        if use_or:
            combined = combined | q
        else:
            combined = combined & q
    return queryset.filter(combined).distinct()
