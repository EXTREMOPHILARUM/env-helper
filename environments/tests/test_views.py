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
def test_environment_create_view(authenticated_client, user):
    """Test environment create view."""
    data = {
        'name': 'test-env',
        'description': 'Test Environment',
        'environment_type': 'vscode',
        'image': 'python:3.11-slim',
        'port': 8080,
        'environment_variables': '{"PUID": "1000", "PGID": "1000", "TZ": "UTC"}'
    }
    response = authenticated_client.post(reverse('environment_create'), data)
    assert response.status_code == 302  # Redirect after successful creation
    
    environment = Environment.objects.get(name='test-env')
    assert environment.created_by == user
    assert environment.environment_variables == {'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}

@pytest.mark.django_db
def test_environment_delete_view(authenticated_client, environment):
    """Test environment delete view."""
    response = authenticated_client.post(reverse('environment_delete', kwargs={'pk': environment.pk}))
    assert response.status_code == 302  # Redirect after successful deletion
    assert not Environment.objects.filter(pk=environment.pk).exists()

@pytest.mark.django_db
@pytest.mark.parametrize('action', ['start', 'stop'])
def test_environment_actions(authenticated_client, environment, mocker, action):
    """Test environment start/stop actions."""
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    
    if action == 'start':
        mock_container = mocker.MagicMock(id='test_container')
        mock_containers.run.return_value = mock_container
        mock_volumes.get.side_effect = docker.errors.NotFound('Volume not found')
        mock_volumes.create.return_value = mock_volume
    else:
        environment.is_running = True
        environment.container_id = 'test_container'
        environment.save()
        mock_container = mocker.MagicMock()
        mock_container.stop.return_value = None
        mock_container.remove.return_value = None
        mock_containers.get.return_value = mock_container
    
    mock_client.containers = mock_containers
    mock_client.volumes = mock_volumes
    mocker.patch('docker.from_env', return_value=mock_client)
    
    response = authenticated_client.post(reverse(f'environment_{action}', kwargs={'pk': environment.pk}))
    assert response.status_code == 302  # Redirect after action
    environment.refresh_from_db()
    assert environment.is_running == (action == 'start')

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
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_container = mocker.MagicMock(id='test_container')
    mock_containers.run.return_value = mock_container
    mock_client.containers = mock_containers
    
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_volumes.get.side_effect = docker.errors.NotFound('Volume not found')
    mock_volumes.create.return_value = mock_volume
    mock_client.volumes = mock_volumes
    
    mocker.patch('docker.from_env', return_value=mock_client)
    
    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    assert response.status_code == 302
    mock_containers.run.assert_called_once()

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
