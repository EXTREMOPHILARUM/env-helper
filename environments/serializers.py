from rest_framework import serializers
from .models import Environment

class EnvironmentSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    
    class Meta:
        model = Environment
        fields = [
            'id', 'name', 'description', 'environment_type',
            'created_by', 'created_at', 'updated_at',
            'image', 'port', 'volume_path', 'environment_variables',
            'is_running', 'container_id'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'is_running', 'container_id']
