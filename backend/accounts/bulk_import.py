"""Importação em massa de usuários via CSV.

Formato esperado (cabeçalho obrigatório na primeira linha):
username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration

Exemplo para aluno:
username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration
aluno.test01,STUDENT,Ana,Teste,ana.teste@exemplo.local,Uma-senha-segura-123,AT001,ADS,ADS-2026.2,

Exemplo para professor:
username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration
prof.test01,PROFESSOR,Carlos,Teste,carlos.teste@exemplo.local,Uma-senha-segura-123,,ADS,,P001

Regras:
- username: obrigatório, único, alfanumérico com underline/hífen
- role: STUDENT ou PROFESSOR (obrigatório)
- first_name, last_name: obrigatórios
- email: opcional, deve ser único se informado
- password: obrigatório, mínimo 8 caracteres
- ra: obrigatório para STUDENT, único
- course_code: obrigatório para STUDENT, curso deve existir
- class_offering_code: obrigatório para STUDENT, turma deve existir no curso
- registration: obrigatório para PROFESSOR, único
"""

import csv
import hashlib
import io
import logging

from academic.models import ClassOffering, Course, ProfessorProfile, StudentProfile
from django.db import transaction
from rest_framework import serializers

from accounts.models import User

logger = logging.getLogger(__name__)

USERNAME_REGEX = r"^[a-zA-Z0-9._-]+$"


class BulkImportRowSerializer(serializers.Serializer):
    """Valida uma única linha do CSV de importação."""

    username = serializers.CharField(max_length=150, required=True)
    role = serializers.ChoiceField(choices=[User.Role.STUDENT, User.Role.PROFESSOR], required=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, required=True, write_only=True)
    ra = serializers.CharField(max_length=40, required=False, allow_blank=True)
    course_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    class_offering_code = serializers.CharField(max_length=30, required=False, allow_blank=True)
    registration = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate_username(self, value):
        import re

        if not re.match(USERNAME_REGEX, value):
            raise serializers.ValidationError(
                "Usuário deve conter apenas letras, números, underline e hífen."
            )
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Usuário já existe.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("E-mail já cadastrado.")
        return value

    def validate_ra(self, value):
        if not value:
            return value
        if StudentProfile.objects.filter(ra=value.upper()).exists():
            raise serializers.ValidationError("RA já cadastrado.")
        return value.upper()

    def validate_registration(self, value):
        if not value:
            return value
        if ProfessorProfile.objects.filter(registration=value).exists():
            raise serializers.ValidationError("Matrícula de professor já cadastrada.")
        return value

    def validate(self, attrs):
        role = attrs.get("role")
        ra = attrs.get("ra")
        course_code = attrs.get("course_code")
        class_offering_code = attrs.get("class_offering_code")
        registration = attrs.get("registration")

        if role == User.Role.STUDENT:
            if not ra:
                raise serializers.ValidationError({"ra": "Obrigatório para aluno."})
            if not course_code:
                raise serializers.ValidationError(
                    {"course_code": "Obrigatório para aluno."}
                )
            if not class_offering_code:
                raise serializers.ValidationError(
                    {"class_offering_code": "Obrigatório para aluno."}
                )
            try:
                course = Course.objects.get(code=course_code)
            except Course.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"course_code": f"Curso '{course_code}' não encontrado."}
                ) from exc
            try:
                offering = ClassOffering.objects.get(code=class_offering_code)
            except ClassOffering.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {
                        "class_offering_code": (
                            f"Turma '{class_offering_code}' não encontrada."
                        )
                    }
                ) from exc
            attrs["_course"] = course
            attrs["_offering"] = offering

        if role == User.Role.PROFESSOR:
            if not registration:
                raise serializers.ValidationError(
                    {"registration": "Obrigatório para professor."}
                )

        return attrs


class BulkImportResult:
    """Resultado da importação em massa."""

    def __init__(self):
        self.created = []
        self.errors = []

    def add_success(self, username, role):
        self.created.append({"username": username, "role": role})

    def add_error(self, row, field, message):
        self.errors.append({"row": row, "field": field, "message": message})

    @property
    def success_count(self):
        return len(self.created)

    @property
    def error_count(self):
        return len(self.errors)

    @property
    def success(self):
        return self.error_count == 0


def import_users_from_csv(file_obj, actor):
    """Importa usuários de um arquivo CSV.

    Retorna um BulkImportResult. A operação é atômica: se houver qualquer erro,
    nenhuma alteração é persistida no banco.
    """
    result = BulkImportResult()
    decoded = io.TextIOWrapper(file_obj, encoding="utf-8-sig")
    reader = csv.DictReader(decoded)

    if reader.fieldnames is None:
        result.add_error(0, "arquivo", "Arquivo CSV vazio ou sem cabeçalho.")
        return result

    required_headers = {"username", "role", "first_name", "last_name", "password"}
    missing = required_headers - set(reader.fieldnames)
    if missing:
        missing_str = ", ".join(sorted(missing))
        result.add_error(0, "cabeçalho", f"Colunas obrigatórias ausentes: {missing_str}")
        return result

    rows = list(reader)
    if not rows:
        result.add_error(0, "arquivo", "Nenhuma linha de dados encontrada.")
        return result

    # Valida todas as linhas primeiro (sem gravar nada)
    validated_rows = []
    for idx, row in enumerate(rows, start=2):  # linha 1 é cabeçalho
        serializer = BulkImportRowSerializer(data=row)
        if not serializer.is_valid():
            for field, messages in serializer.errors.items():
                for msg in messages:
                    result.add_error(idx, field, msg)
        else:
            validated_rows.append((idx, serializer.validated_data))

    if result.error_count > 0:
        return result

    # Cria todos os usuários em transação atômica
    try:
        with transaction.atomic():
            for _row_idx, data in validated_rows:
                role = data["role"]
                username = data["username"]
                password = data["password"]

                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    email=data.get("email", ""),
                    role=role,
                    is_active=True,
                )

                if role == User.Role.STUDENT:
                    course = data["_course"]
                    offering = data["_offering"]
                    ra = data["ra"]

                    # Gerar hash a partir do username+RA (não é CPF real,
                    # apenas identificador sintético para o campo obrigatório)
                    cpf_hash = hashlib.sha256(f"{username}:{ra}".encode()).hexdigest()
                    cpf_last4 = ra[-4:] if ra else "0000"

                    StudentProfile.objects.create(
                        user=user,
                        ra=ra,
                        course=course,
                        class_offering=offering,
                        cpf_hash=cpf_hash,
                        cpf_last4=cpf_last4,
                    )

                if role == User.Role.PROFESSOR:
                    ProfessorProfile.objects.create(
                        user=user,
                        registration=data["registration"],
                    )

                result.add_success(username, role)

    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha na importação em massa")
        result.add_error(0, "sistema", str(exc))

    return result
