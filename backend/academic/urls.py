from django.urls import path
from projects.grading_views import IndividualGradeView
from rest_framework.routers import DefaultRouter

from .views import (
    ApproveRoomTransferView,
    ClassOfferingViewSet,
    CloseRoomView,
    CourseViewSet,
    DeclineRoomTransferView,
    EligibleRoomStudentListView,
    MyExpertiseDetailView,
    MyExpertiseListCreateView,
    ProfessorProfileViewSet,
    ProfessorSearchView,
    PullRoomStudentView,
    RoomDetailView,
    RoomListCreateView,
    RoomStudentListView,
    RoomTransferRequestListView,
    StudentProfileViewSet,
    SubjectViewSet,
)

router = DefaultRouter()
router.register("courses", CourseViewSet)
router.register("subjects", SubjectViewSet)
router.register("class-offerings", ClassOfferingViewSet)
router.register("students", StudentProfileViewSet)
router.register("professors", ProfessorProfileViewSet)
urlpatterns = [
    path("rooms/", RoomListCreateView.as_view()),
    path("rooms/<uuid:room_id>/", RoomDetailView.as_view()),
    path("rooms/<uuid:room_id>/pull-student/", PullRoomStudentView.as_view()),
    path("rooms/<uuid:room_id>/close/", CloseRoomView.as_view()),
    path("rooms/<uuid:room_id>/students/", RoomStudentListView.as_view()),
    path("eligible-students/", EligibleRoomStudentListView.as_view()),
    path("professors/search/", ProfessorSearchView.as_view()),
    path(
        "students/<int:student_id>/individual-grade/",
        IndividualGradeView.as_view(),
    ),
    path("my-expertise/", MyExpertiseListCreateView.as_view()),
    path("my-expertise/<uuid:pk>/", MyExpertiseDetailView.as_view()),
    path("room-transfer-requests/", RoomTransferRequestListView.as_view()),
    path("room-transfer-requests/<uuid:transfer_id>/approve/", ApproveRoomTransferView.as_view()),
    path("room-transfer-requests/<uuid:transfer_id>/decline/", DeclineRoomTransferView.as_view()),
] + router.urls
