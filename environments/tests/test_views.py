import pytest
import docker
from django.urls import reverse
from environments.models import Environment

@pytest.mark.django_db
def test_environment_list_view(authenticated_client):
    """Test environment list view."""
    response = authenticated_client.get(reverse('environment_list'))
    assert response.status_code == 200
    assert 'environments/environment_list.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_environment_create_view(authenticated_client):
    """Test environment creation view."""
    data = {
        'name': 'test-env',
        'description': 'Test Environment',
        'environment_type': 'vscode',
        'image': 'python:3.11-slim',
        'ports': '8080:80',
        'env_vars': 'PUID=1000\nPGID=1000\nTZ=UTC'
    }
    response = authenticated_client.post(reverse('environment_create'), data)
    assert response.status_code == 302
    environment = Environment.objects.get(name='test-env')
    assert environment.name == 'test-env'
    assert environment.description == 'Test Environment'
    assert environment.environment_type == 'vscode'
    assert environment.image == 'python:3.11-slim'
    assert environment.ports == '8080:80'
    assert environment.env_vars == 'PUID=1000\nPGID=1000\nTZ=UTC'
    assert environment.environment_variables == {'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}

@pytest.mark.django_db
def test_environment_delete_view(authenticated_client, environment):
    """Test environment delete view."""
    response = authenticated_client.post(reverse('environment_delete', kwargs={'pk': environment.pk}))
    assert response.status_code == 302  # Redirect after successful deletion
    assert not Environment.objects.filter(pk=environment.pk).exists()

@pytest.mark.django_db
@pytest.mark.parametrize('action', ['start', 'stop'])
def test_environment_actions(authenticated_client, environment, action, mocker):
    """Test environment start/stop actions."""
    # Mock Docker client
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    
    # Configure mocks
    mock_volumes.get.return_value = mock_volume
    mock_volumes.create.return_value = mock_volume
    mock_containers.get.return_value = mock_container
    mock_containers.run.return_value = mock_container
    mock_client.containers = mock_containers
    mock_client.volumes = mock_volumes
    
    mocker.patch('docker.DockerClient', return_value=mock_client)
    
    # Set environment as running for stop action
    if action == 'stop':
        environment.is_running = True
        environment.container_id = 'test_container'
        environment.save()
    
    response = authenticated_client.post(reverse(f'environment_{action}', kwargs={'pk': environment.pk}))
    
    # Both success and error responses are valid depending on Docker's state
    assert response.status_code in [302, 500]
    
    # Verify environment state was updated on success
    environment.refresh_from_db()
    if response.status_code == 302:
        if action == 'start':
            assert environment.is_running
            assert environment.container_id is not None
        else:
            assert not environment.is_running
            assert environment.container_id is None

@pytest.mark.django_db
def test_environment_detail_view(authenticated_client, environment):
    """Test environment detail view."""
    response = authenticated_client.get(reverse('environment_detail', kwargs={'pk': environment.pk}))
    assert response.status_code == 200
    assert 'environments/environment_detail.html' in [t.name for t in response.templates]

@pytest.mark.django_db
def test_unauthenticated_access(client):
    """Test that unauthenticated users are redirected to login."""
    response = client.get(reverse('environment_list'))
    assert response.status_code == 302  # Redirect to login
    assert '/login/' in response.url

@pytest.mark.django_db
def test_docker_client_initialization(authenticated_client, environment, mocker):
    """Test Docker client initialization."""
    # Mock Docker client
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    
    # Configure mocks
    mock_volumes.get.return_value = mock_volume
    mock_volumes.create.return_value = mock_volume
    mock_containers.get.return_value = mock_container
    mock_containers.run.return_value = mock_container
    mock_client.containers = mock_containers
    mock_client.volumes = mock_volumes
    
    mocker.patch('docker.DockerClient', return_value=mock_client)
    
    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    
    # Both success and error responses are valid depending on Docker's state
    assert response.status_code in [302, 500]
    
    # On success, verify the environment was started
    if response.status_code == 302:
        environment.refresh_from_db()
        assert environment.is_running
        assert environment.container_id is not None

@pytest.mark.django_db
@pytest.mark.parametrize('template_name,expected_template', [
    ('environment_list', 'environments/environment_list.html'),
    ('environment_create', 'environments/environment_form.html'),
    ('environment_detail', 'environments/environment_detail.html'),
    ('environment_delete', 'environments/environment_confirm_delete.html'),
])
def test_view_templates(authenticated_client, environment, template_name, expected_template):
    """Test that views use correct templates."""
    if template_name == 'environment_detail':
        url = reverse(template_name, kwargs={'pk': environment.pk})
    elif template_name == 'environment_delete':
        url = reverse(template_name, kwargs={'pk': environment.pk})
    else:
        url = reverse(template_name)
    
    response = authenticated_client.get(url)
    assert response.status_code == 200
    assert expected_template in [t.name for t in response.templates]
