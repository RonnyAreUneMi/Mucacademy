from rest_framework import serializers

from core.models import CertificateBatch


class LoteListSerializer(serializers.ModelSerializer):
    administrador_username = serializers.CharField(source='administrator.username', read_only=True, allow_null=True)
    total_certificados = serializers.IntegerField(read_only=True, required=False)
    facultad_display = serializers.CharField(source='get_faculty_display', read_only=True)
    plantilla_display = serializers.CharField(source='get_template_display', read_only=True)

    class Meta:
        model = CertificateBatch
        fields = [
            'id', 'name', 'faculty', 'facultad_display',
            'template', 'plantilla_display', 'customize_design',
            'color_primary', 'color_secondary', 'color_tertiary', 'color_text',
            'administrator', 'administrador_username',
            'is_active', 'created_at', 'total_certificados',
        ]
        read_only_fields = ('created_at',)


class LoteDetailSerializer(LoteListSerializer):
    class Meta(LoteListSerializer.Meta):
        fields = LoteListSerializer.Meta.fields + [
            'body_text', 'excel_file',
            'signature_name_1', 'signature_role_1',
            'signature_name_2', 'signature_role_2',
            'signature_name_3', 'signature_role_3',
            'signature_name_4', 'signature_role_4',
            'signature_inst_1', 'signature_inst_2', 'signature_inst_3', 'signature_inst_4',
            'header_logo_1', 'header_logo_2', 'header_logo_3',
            'signatures_position',
        ]


class LoteWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateBatch
        fields = [
            'name', 'faculty', 'template', 'customize_design',
            'color_primary', 'color_secondary', 'color_tertiary', 'color_text',
            'body_text', 'excel_file', 'is_active',
            'signature_inst_1', 'signature_inst_2', 'signature_inst_3', 'signature_inst_4',
            'signature_name_1', 'signature_role_1',
            'signature_name_2', 'signature_role_2',
            'signature_name_3', 'signature_role_3',
            'signature_name_4', 'signature_role_4',
            'header_logo_1', 'header_logo_2', 'header_logo_3',
            'signatures_position',
        ]
