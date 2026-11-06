"""Physical venues and the single, transactional Mostra scheduling workflow."""

from datetime import datetime

from academic.models import ProfessorProfile
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .evaluation import evaluator_conflicts
from .models import (
    Project,
    ProjectGroup,
    ShowcaseBuilding,
    ShowcaseDay,
    ShowcaseEntry,
    ShowcaseRoom,
    next_number,
)
from .services import audit
from .showcase import _notify_group_members, require_showcase_staff


def building_code(number):
    code = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        code = chr(65 + remainder) + code
    return code


class NameInput(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)


def half_hour(value):
    if value.minute not in {0, 30} or value.second or value.microsecond:
        raise ValidationError("Use intervalos de meia hora (00 ou 30 minutos).")


class DayInput(serializers.ModelSerializer):
    class Meta:
        model = ShowcaseDay
        fields = ["id", "date", "start_time", "end_time"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        for field in ("start_time", "end_time"):
            half_hour(attrs[field])
        if attrs["end_time"] <= attrs["start_time"]:
            raise ValidationError("O fim deve ser posterior ao início, no mesmo dia.")
        return attrs


class ScheduleInput(serializers.Serializer):
    group = serializers.UUIDField()
    day = serializers.UUIDField()
    room = serializers.UUIDField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    expected_updated_at = serializers.DateTimeField(required=False)


def entry_data(entry):
    if entry is None:
        return None
    return {
        "id": str(entry.pk),
        "date": entry.date,
        "end_date": entry.end_date,
        "day": str(entry.day_id) if entry.day_id else None,
        "room": str(entry.room_id) if entry.room_id else None,
        "location": (
            f"{entry.room.building.name} / {entry.room.name}" if entry.room_id else entry.location
        ),
        "status": entry.status,
        "updated_at": entry.updated_at,
        "evaluator_id": str(entry.group.evaluator_id) if entry.group.evaluator_id else None,
        "evaluator_name": (
            entry.group.evaluator.user.get_full_name() or entry.group.evaluator.user.username
            if entry.group.evaluator_id
            else None
        ),
    }


@transaction.atomic
def schedule_group(*, actor, data):
    require_showcase_staff(actor)
    group = get_object_or_404(ProjectGroup.objects.select_for_update(), pk=data["group"])
    project = Project.objects.select_for_update().get(pk=group.project_id)
    if not group.is_active or not project.is_active or project.status != Project.Status.APPROVED:
        raise ValidationError("Somente grupos ativos de projetos aprovados podem ser agendados.")
    if not hasattr(project, "forwarding"):
        raise ValidationError("O projeto precisa estar encaminhado ao Administrador.")
    if project.cancellation_requests.filter(status="PENDING").exists():
        raise ValidationError("Há cancelamento pendente para este projeto.")
    # A day lock protects overlapping room reservations even when the room is still empty.
    day = get_object_or_404(ShowcaseDay.objects.select_for_update(), pk=data["day"])
    room = get_object_or_404(ShowcaseRoom.objects.select_related("building"), pk=data["room"])
    start, end = data["start_time"], data["end_time"]
    half_hour(start)
    half_hour(end)
    if not day.start_time <= start < end <= day.end_time:
        raise ValidationError("Horário fora da janela do dia ou duração inválida.")
    start_at = timezone.make_aware(datetime.combine(day.date, start))
    end_at = timezone.make_aware(datetime.combine(day.date, end))
    entry = ShowcaseEntry.objects.select_for_update().filter(group=group).first()
    if entry and entry.status in {"PRESENTED", "ABSENT"}:
        raise ValidationError("Uma apresentação com presença registrada não pode ser reagendada.")
    if entry and data.get("expected_updated_at") != entry.updated_at:
        raise ValidationError("A agenda mudou. Atualize a tela antes de tentar novamente.")
    # Uma sala pode receber múltiplos grupos no mesmo horário; apenas o avaliador tem conflito.
    if group.evaluator_id:
        professor = (
            ProfessorProfile.objects.select_for_update(of=("self",))
            .select_related("user")
            .get(pk=group.evaluator_id)
        )
        if not professor.user.is_active or professor.user.role != "PROFESSOR":
            raise ValidationError("O avaliador está inativo. Escolha outro antes de reagendar.")
        if evaluator_conflicts(professor.pk, group.pk, start_at, end_at):
            raise ValidationError("O avaliador já possui outra apresentação neste horário.")
    if entry is None:
        entry = ShowcaseEntry(group=group)
    entry.day, entry.room = day, room
    entry.date, entry.end_date = start_at, end_at
    entry.location = f"{room.building.name} / {room.name}"[:200]
    entry.status, entry.decided_by = "SCHEDULED", actor
    entry.save()
    audit(actor, "SCHEDULE_SHOWCASE", entry, ["day", "room", "date", "end_date"])
    _notify_group_members(
        actor,
        group,
        "Mostra agendada",
        f"Apresentação em {day.date:%d/%m/%Y}, {start:%H:%M}–{end:%H:%M}, {entry.location}.",
        project,
    )
    return entry


class PlanningView(APIView):
    def get(self, request):
        require_showcase_staff(request.user)
        eligible = Q(
            is_active=True,
            project__is_active=True,
            project__status="APPROVED",
            project__forwarding__isnull=False,
        )
        groups = (
            ProjectGroup.objects.filter(eligible | Q(showcase_entry__isnull=False))
            .select_related(
                "project__forwarding",
                "showcase_entry__room__building",
                "showcase_entry__group__evaluator__user",
            )
            .prefetch_related("members__student__user")
            .order_by("project__number", "id")
        )
        query = request.query_params.get("q", "").strip()[:100]
        for word in query.split():
            terms = (
                Q(project__name__icontains=word)
                | Q(name__icontains=word)
                | Q(members__is_active=True, members__student__user__first_name__icontains=word)
                | Q(members__is_active=True, members__student__user__last_name__icontains=word)
                | Q(members__is_active=True, members__student__user__username__icontains=word)
            )
            if word.lstrip("#").isdigit() and int(word.lstrip("#")) < 2**63:
                terms |= Q(project__number=int(word.lstrip("#")))
            groups = groups.filter(terms)
        data = []
        for group in groups.distinct():
            members = [m for m in group.members.all() if m.is_active]
            entry = getattr(group, "showcase_entry", None)
            data.append(
                {
                    "id": str(group.pk),
                    "name": group.name,
                    "project": str(group.project_id),
                    "number": group.project.number,
                    "eligible": (
                        group.is_active
                        and group.project.is_active
                        and group.project.status == "APPROVED"
                        and hasattr(group.project, "forwarding")
                    ),
                    "project_name": group.project.name,
                    "members": [
                        m.student.user.get_full_name() or m.student.user.username for m in members
                    ],
                    "entry": entry_data(entry),
                }
            )
        buildings = list(ShowcaseBuilding.objects.values("id", "number", "code", "name"))
        rooms = list(ShowcaseRoom.objects.values("id", "building", "number", "name"))
        # Calendar entries are independent of the search; filtering cannot hide occupied slots.
        entries = ShowcaseEntry.objects.exclude(status="CANCELLED").select_related(
            "room__building", "group__project", "group__evaluator__user"
        )
        return Response(
            {
                "buildings": buildings,
                "rooms": rooms,
                "days": DayInput(ShowcaseDay.objects.all(), many=True).data,
                "groups": data,
                "entries": [
                    {
                        **entry_data(e),
                        "group": str(e.group_id),
                        "project_name": e.group.project.name,
                        "number": e.group.project.number,
                    }
                    for e in entries
                ],
            }
        )

    def post(self, request):
        require_showcase_staff(request.user)
        serializer = ScheduleInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            entry_data(schedule_group(actor=request.user, data=serializer.validated_data))
        )


class BuildingsView(APIView):
    @transaction.atomic
    def post(self, request):
        require_showcase_staff(request.user)
        serializer = NameInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        number = next_number("showcase-building")
        code = building_code(number)
        item = ShowcaseBuilding.objects.create(
            number=number, code=code, name=serializer.validated_data.get("name") or f"Prédio {code}"
        )
        audit(request.user, "CREATE_SHOWCASE_BUILDING", item, ["name", "code"])
        return Response({"id": str(item.pk)}, status=201)

    def patch(self, request, building_id):
        require_showcase_staff(request.user)
        item = get_object_or_404(ShowcaseBuilding, pk=building_id)
        serializer = NameInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("name"):
            raise ValidationError("Informe o nome do prédio.")
        item.name = serializer.validated_data["name"]
        item.save(update_fields=["name"])
        audit(request.user, "RENAME_SHOWCASE_BUILDING", item, ["name"])
        return Response({"id": str(item.pk)})


class RoomsView(APIView):
    @transaction.atomic
    def post(self, request, building_id):
        require_showcase_staff(request.user)
        building = get_object_or_404(ShowcaseBuilding, pk=building_id)
        serializer = NameInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        number = next_number(f"showcase-room-{building.pk}")
        item = ShowcaseRoom.objects.create(
            building=building,
            number=number,
            name=serializer.validated_data.get("name") or f"Sala {number}",
        )
        audit(request.user, "CREATE_SHOWCASE_ROOM", item, ["name", "number"])
        return Response({"id": str(item.pk)}, status=201)

    def patch(self, request, room_id):
        require_showcase_staff(request.user)
        item = get_object_or_404(ShowcaseRoom, pk=room_id)
        serializer = NameInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get("name"):
            raise ValidationError("Informe o nome da sala.")
        item.name = serializer.validated_data["name"]
        item.save(update_fields=["name"])
        audit(request.user, "RENAME_SHOWCASE_ROOM", item, ["name"])
        return Response({"id": str(item.pk)})


class DaysView(APIView):
    def post(self, request):
        require_showcase_staff(request.user)
        serializer = DayInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = serializer.save()
        audit(request.user, "CREATE_SHOWCASE_DAY", day, ["date", "start_time", "end_time"])
        return Response(DayInput(day).data, status=201)
