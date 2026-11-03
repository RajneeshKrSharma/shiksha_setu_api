from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.permissions import CapabilityGate
from apps.accounts.domain.capabilities import MANAGE_QUESTION_BANK, PREPARE_QUESTIONS
from config.container import container

from ..domain.entities import ScanFile
from .serializers import PageTextOut

_TEST_PAGE = Path(__file__).with_name("test_page.html")


class ReadHandwritingView(APIView):
    """POST photos or PDFs as multipart field `files`; the text written on each comes back."""

    permission_classes = [CapabilityGate.of(read=(), write=(PREPARE_QUESTIONS, MANAGE_QUESTION_BANK))]
    parser_classes = [MultiPartParser]

    def post(self, request):
        files = [ScanFile(upload.name, upload.content_type, upload.read())
                 for upload in request.FILES.getlist("files")]
        pages = container.read_handwriting().call(container.actor(request.user), files)
        return Response({"pages": PageTextOut(pages, many=True).data})


class ReadHandwritingTestView(APIView):
    """Same as ReadHandwritingView with no sign-in, for trying it by hand. DEBUG only."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not settings.DEBUG:
            raise Http404()
        files = [ScanFile(upload.name, upload.content_type, upload.read())
                 for upload in request.FILES.getlist("files")]
        pages = container.read_handwriting_without_sign_in().call(None, files)
        return Response({"pages": PageTextOut(pages, many=True).data})


class TestPageView(APIView):
    """A plain page for trying the reader by hand. Only served while DEBUG is on."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        if not settings.DEBUG:
            raise Http404()
        return HttpResponse(_TEST_PAGE.read_text(encoding="utf-8"), content_type="text/html")
