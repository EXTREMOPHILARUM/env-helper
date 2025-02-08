import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from environments.models import Environment

@pytest.mark.django_db
def test_environment_creation(user):
    """Test environment creation with valid data."""
    environment = Environment.objects.create(
        name='test-env',
        description='Test Environment',
        environment_type='vscode',
        created_by=user,
        image='python:3.11-slim',
        port=8080,
        environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
    )
    assert environment.name == 'test-env'
    assert environment.volume_name.startswith('env_helper_vscode_')
    assert len(environment.volume_name) > len('env_helper_vscode_')

@pytest.mark.django_db
def test_environment_str_representation(environment):
    """Test environment string representation."""
    assert str(environment) == 'test-env (vscode)'

@pytest.mark.django_db
def test_environment_unique_name_per_user(user):
    """Test that environment names must be unique per user."""
    Environment.objects.create(
        name='test-env',
        description='Test Environment',
        environment_type='vscode',
        created_by=user,
        image='python:3.11-slim',
        port=8080,
        environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
    )
    
    with pytest.raises(ValidationError):
        Environment.objects.create(
            name='test-env',
            description='Another Test Environment',
            environment_type='vscode',
            created_by=user,
            image='python:3.11-slim',
            port=8080,
            environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
        )

@pytest.mark.django_db
def test_environment_name_validation():
    """Test environment name validation."""
    user = User.objects.create_user('testuser')
    
    # Valid names
    valid_names = [
        'test-env',
        'test_env',
        'test.env',
        'test123',
        'TEST_ENV',
    ]
    
    for name in valid_names:
        environment = Environment(
            name=name,
            description='Test Environment',
            environment_type='vscode',
            created_by=user,
            image='python:3.11-slim',
            port=8080,
            environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
        )
        environment.full_clean()  # Should not raise ValidationError
    
    # Invalid names
    invalid_names = [
        'test env',  # Contains space
        'test@env',  # Contains @
        'test/env',  # Contains /
        'test\\env',  # Contains \
        '_test',  # Starts with underscore
        '.test',  # Starts with period
        '-test',  # Starts with hyphen
    ]
    
    for name in invalid_names:
        environment = Environment(
            name=name,
            description='Test Environment',
            environment_type='vscode',
            created_by=user,
            image='python:3.11-slim',
            port=8080,
            environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
        )
        with pytest.raises(ValidationError):
            environment.full_clean()

@pytest.mark.django_db
def test_environment_container_name(environment):
    """Test container name generation."""
    # Test basic container name
    assert environment.container_name == f'env-{environment.created_by.username}-{environment.name}'
    
    # Test container name with special characters
    environment.name = 'test.env_1-2'
    assert environment.container_name == 'env-testuser-test.env_1-2'
    
    # Test container name with invalid characters
    environment.name = 'test@env'
    assert environment.container_name == 'env-testuser-test_env'
    
    # Test container name with spaces
    environment.name = 'test env'
    assert environment.container_name == 'env-testuser-test_env'

@pytest.mark.django_db
def test_environment_volume_name(environment):
    """Test volume name generation."""
    assert environment.volume_name.startswith('env_helper_vscode_')
    assert len(environment.volume_name) == len('env_helper_vscode_') + 8  # 8 characters from uuid
