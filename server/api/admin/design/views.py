from rest_framework import serializers, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import GlobalDesign
from core.base.mixins import log_audit


class DisenoGlobalSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalDesign
        fields = [
            'id', 'template', 'color_primary', 'color_secondary',
            'color_tertiary', 'color_text', 'body_text',
            'signature_inst_1', 'signature_inst_2', 'signature_inst_3',
            'signature_name_4', 'signature_role_4', 'signature_image_4',
            'header_logo_1', 'header_logo_2', 'header_logo_3',
            'signatures_position',
            'signature_1_offset_y', 'signature_1_scale',
            'signature_2_offset_y', 'signature_2_scale',
            'signature_3_offset_y', 'signature_3_scale',
            'signature_4_offset_y', 'signature_4_scale',
            'updated_at',
        ]
        read_only_fields = ('id', 'updated_at')


class DisenoGlobalView(APIView):
    """Singleton: GET devuelve el diseño actual, PATCH lo actualiza."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        diseno = GlobalDesign.load()
        return Response(DisenoGlobalSerializer(diseno).data)

    def patch(self, request):
        diseno = GlobalDesign.load()
        ser = DisenoGlobalSerializer(diseno, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        log_audit(request.user, 'EDITAR_DISENO_GLOBAL', 'Diseño global actualizado')
        return Response(ser.data)
