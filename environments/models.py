from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
import json

def validate_container_name(value):
    """Validate that the name will result in a valid Docker container name."""
    # Docker container names must match [a-zA-Z0-9][a-zA-Z0-9_.-]
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', value):
        raise ValidationError(
            'Name can only contain letters, numbers, underscores, periods, and hyphens, '
            'and must start with a letter or number.'
        )

# Create your models here.

class Environment(models.Model):
    ENVIRONMENT_TYPES = (
        ('vscode', 'VSCode'),
        ('webtop', 'Docker Webtop'),
        ('custom', 'Custom Environment')
    )

    # Default configurations for each environment type
    DEFAULT_CONFIGS = {
        'vscode': {
            'image': 'codercom/code-server:latest',
            'ports': '8443:8080',
            'env_vars': 'PASSWORD=password123\nTZ=UTC',
            'volumes': 'vscode_data:/home/coder',
            'cpu_limit': '1.0',
            'memory_limit': '2g',
            'auto_start': True
        },
        'webtop': {
            'image': 'linuxserver/webtop:ubuntu-kde',
            'ports': '3000:3000',
            'env_vars': 'PUID=1000\nPGID=1000\nTZ=UTC',
            'volumes': 'webtop_config:/config\nwebtop_home:/config/home',
            'cpu_limit': '2.0',
            'memory_limit': '4g',
            'auto_start': True
        },
        'custom': {
            'image': '',
            'ports': '',
            'env_vars': 'TZ=UTC',
            'volumes': '',
            'cpu_limit': '1.0',
            'memory_limit': '2g',
            'auto_start': False
        }
    }

    name = models.CharField(
        max_length=100,
        validators=[validate_container_name],
        help_text='Name can only contain letters, numbers, underscores, periods, and hyphens.'
    )
    description = models.TextField(blank=True)
    environment_type = models.CharField(max_length=10, choices=ENVIRONMENT_TYPES)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Container configuration
    image = models.CharField(max_length=255)
    ports = models.CharField(max_length=255, blank=True, help_text='Comma-separated list of port mappings (e.g., "8080:80,3000:3000")')
    volumes = models.TextField(blank=True, help_text='One volume mount per line in host_path:container_path format')
    env_vars = models.TextField(blank=True, help_text='Environment variables in KEY=value format, one per line')
    cpu_limit = models.CharField(max_length=10, blank=True, help_text='CPU limit (e.g., 0.5, 1.0, 2.0)')
    memory_limit = models.CharField(max_length=10, blank=True, help_text='Memory limit (e.g., 512m, 1g, 2g)')
    auto_start = models.BooleanField(default=False, help_text='Start container automatically on system boot')
    volume_name = models.CharField(max_length=255, blank=True)  # Docker volume name
    environment_variables = models.JSONField(default=dict, blank=True, null=True)
    
    # Container status
    is_running = models.BooleanField(default=False)
    container_id = models.CharField(max_length=64, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('name', 'created_by')  # Names must be unique per user
    
    def __str__(self):
        return f"{self.name} ({self.environment_type})"

    @property
    def ui_port(self):
        """Get the UI port (first host port) from the port mappings."""
        if not self.ports:
            return None
        
        # Get the first port mapping
        port_mappings = [p.strip() for p in self.ports.split(',')]
        if not port_mappings:
            return None
            
        # Parse the first port mapping
        first_mapping = port_mappings[0]
        try:
            host_port = first_mapping.split(':')[0]
            return int(host_port)
        except (IndexError, ValueError):
            return None

    @property
    def env_vars_as_text(self):
        """Convert environment variables to text format."""
        if not self.env_vars:
            return ''
        
        try:
            if isinstance(self.env_vars, str):
                # Try to parse as JSON if it's a string
                env_dict = json.loads(self.env_vars)
            elif isinstance(self.env_vars, dict):
                env_dict = self.env_vars
            else:
                return str(self.env_vars)
            
            # Convert to KEY=value format
            return '\n'.join(f"{key}={value}" for key, value in env_dict.items())
        except (json.JSONDecodeError, AttributeError):
            return str(self.env_vars)

    def clean(self):
        """Additional model validation."""
        super().clean()
        
        # Only validate container name if created_by is set
        if hasattr(self, 'created_by') and self.created_by is not None:
            try:
                container_name = self.container_name
                validate_container_name(container_name)
            except ValidationError as e:
                raise ValidationError({
                    'name': f'This name would create an invalid container name "{container_name}". {str(e)}'
                })
    
    def save(self, *args, **kwargs):
        # Run full validation before saving
        self.full_clean()
        
        # Generate a unique volume name if not set
        if not self.volume_name:
            import uuid
            self.volume_name = f"env_helper_{self.environment_type}_{uuid.uuid4().hex[:8]}"
        super().save(*args, **kwargs)
    
    @property
    def container_name(self):
        """Generate a unique container name."""
        # Replace any invalid characters with underscores
        safe_username = re.sub(r'[^a-zA-Z0-9_.-]', '_', self.created_by.username)
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', self.name)
        return f'env-{safe_username}-{safe_name}'
