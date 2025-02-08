from django import forms
from django.core.exceptions import ValidationError
import json

from .models import Environment

class EnvironmentForm(forms.ModelForm):
    class Meta:
        model = Environment
        fields = [
            'name', 'description', 'environment_type', 'image',
            'ports', 'volumes', 'env_vars', 'cpu_limit',
            'memory_limit', 'auto_start'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'volumes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': '/host/path:/container/path\n/data:/app/data'
            }),
            'env_vars': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'KEY1=value1\nKEY2=value2'
            }),
            'ports': forms.TextInput(attrs={
                'placeholder': '8080:80, 3000:3000'
            }),
            'cpu_limit': forms.TextInput(attrs={
                'placeholder': '1.0'
            }),
            'memory_limit': forms.TextInput(attrs={
                'placeholder': '2g'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Debug logging
        if self.instance and self.instance.pk:
            print(f"Editing environment {self.instance.pk}")
            print(f"Ports: {self.instance.ports}")
            print(f"Env vars (raw): {self.instance.env_vars}")
            print(f"Volumes (raw): {self.instance.volumes}")
            
            # Convert env_vars to text format for initial display
            if self.instance.env_vars:
                try:
                    env_dict = {}
                    if isinstance(self.instance.env_vars, str):
                        env_dict = json.loads(self.instance.env_vars)
                    else:
                        env_dict = self.instance.env_vars
                    
                    # Convert to KEY=value format
                    env_vars_text = '\n'.join(f"{key}={value}" for key, value in env_dict.items())
                    print(f"Env vars (converted): {env_vars_text}")
                    self.initial['env_vars'] = env_vars_text
                except (json.JSONDecodeError, AttributeError) as e:
                    print(f"Error converting env vars: {e}")
                    if isinstance(self.instance.env_vars, dict):
                        self.initial['env_vars'] = '\n'.join(f"{key}={value}" for key, value in self.instance.env_vars.items())
                    else:
                        self.initial['env_vars'] = str(self.instance.env_vars)
            
            # Convert volumes to text format for initial display
            if self.instance.volumes:
                try:
                    if isinstance(self.instance.volumes, str):
                        # Already in the correct format
                        self.initial['volumes'] = self.instance.volumes
                    elif isinstance(self.instance.volumes, dict):
                        # Convert dict to volume:path format
                        self.initial['volumes'] = '\n'.join(f"{name}:{path}" for name, path in self.instance.volumes.items())
                    else:
                        self.initial['volumes'] = str(self.instance.volumes)
                    print(f"Volumes (converted): {self.initial['volumes']}")
                except Exception as e:
                    print(f"Error converting volumes: {e}")
                    self.initial['volumes'] = str(self.instance.volumes)
            
            print(f"Volumes: {self.instance.volumes}")
            
            # If this is a new environment and environment_type is set
        if not self.instance.pk and 'environment_type' in self.data:
            env_type = self.data['environment_type']
            if env_type in Environment.DEFAULT_CONFIGS:
                # Only set defaults for empty fields
                config = Environment.DEFAULT_CONFIGS[env_type]
                for field, value in config.items():
                    if not self.data.get(field):
                        self.data[field] = value

    def clean_env_vars(self):
        """Convert environment variables from text format to dict."""
        data = self.cleaned_data['env_vars']
        if not data:
            return {}

        env_dict = {}
        try:
            # If it's already a JSON string, try to parse it
            if data.startswith('{') and data.endswith('}'):
                return json.loads(data)
            
            # Otherwise parse as KEY=value format
            for line in data.strip().split('\n'):
                if line.strip():
                    if '=' not in line:
                        raise ValidationError(f"Invalid environment variable format: {line}")
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        raise ValidationError("Environment variable key cannot be empty")
                    env_dict[key] = value
            return env_dict
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format for environment variables")
        except Exception as e:
            raise ValidationError(f"Error parsing environment variables: {str(e)}")

    def clean_ports(self):
        """Validate port mappings format."""
        data = self.cleaned_data['ports']
        if not data:
            return ''
        
        # Split by comma and validate each port mapping
        port_mappings = [p.strip() for p in data.split(',')]
        for mapping in port_mappings:
            if ':' not in mapping:
                raise ValidationError('Port mapping must be in format host_port:container_port')
            host_port, container_port = mapping.split(':')
            try:
                if not (1 <= int(host_port) <= 65535 and 1 <= int(container_port) <= 65535):
                    raise ValidationError('Ports must be between 1 and 65535')
            except ValueError:
                raise ValidationError('Ports must be valid numbers')
        
        return data

    def clean_volumes(self):
        """Validate volume mount format."""
        data = self.cleaned_data['volumes']
        if not data:
            return ''
        
        for line in data.strip().split('\n'):
            if ':' not in line:
                raise ValidationError('Volume mount must be in format host_path:container_path')
        
        return data
