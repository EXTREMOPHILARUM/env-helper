import pytest
import docker
from django.urls import reverse
from docker.errors import APIError, NotFound
from environments.models import Environment

@pytest.mark.django_db
def test_environment_start_with_docker_error(mocker, authenticated_client, environment):
    """Test handling of Docker errors when starting an environment."""
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_containers.run.side_effect = APIError('Docker API error')
    mock_client.containers = mock_containers
    mocker.patch('docker.from_env', return_value=mock_client)

    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    assert response.status_code == 500
    environment.refresh_from_db()
    assert not environment.is_running

@pytest.mark.django_db
def test_environment_stop_with_docker_error(mocker, authenticated_client, environment):
    """Test handling of Docker errors when stopping an environment."""
    environment.is_running = True
    environment.container_id = 'test_container'
    environment.save()

    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    mock_container.stop.side_effect = APIError('Docker API error')
    mock_containers.get.return_value = mock_container
    mock_client.containers = mock_containers
    mocker.patch('docker.from_env', return_value=mock_client)

    response = authenticated_client.post(reverse('environment_stop', kwargs={'pk': environment.pk}))
    assert response.status_code == 500
    environment.refresh_from_db()
    assert environment.is_running

@pytest.mark.django_db
def test_environment_container_cleanup(mocker, authenticated_client, environment):
    """Test container cleanup on environment deletion."""
    environment.is_running = True
    environment.container_id = 'test_container'
    environment.save()

    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    mock_container.stop.return_value = None
    mock_container.remove.return_value = None
    mock_containers.get.return_value = mock_container
    mock_client.containers = mock_containers

    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_volume.remove.return_value = None
    mock_volumes.get.return_value = mock_volume
    mock_client.volumes = mock_volumes

    mocker.patch('docker.from_env', return_value=mock_client)

    response = authenticated_client.delete(reverse('environment_delete', kwargs={'pk': environment.pk}))
    assert response.status_code == 302
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()
    assert not Environment.objects.filter(pk=environment.pk).exists()

@pytest.mark.django_db
def test_docker_volume_management(mocker, authenticated_client, environment):
    """Test Docker volume management."""
    mock_client = mocker.MagicMock()
    
    # Mock volumes
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_volume.remove = mocker.MagicMock()
    mock_volumes.get.side_effect = [NotFound('Volume not found'), mock_volume]
    mock_volumes.create.return_value = mocker.MagicMock(name=environment.volume_name)
    mock_client.volumes = mock_volumes

    # Mock containers
    mock_containers = mocker.MagicMock()
    mock_container = mocker.MagicMock(id='test_container')
    mock_containers.run.return_value = mock_container
    mock_client.containers = mock_containers

    mocker.patch('docker.from_env', return_value=mock_client)

    # Test volume creation
    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    assert response.status_code == 302
    mock_volumes.create.assert_called_once_with(name=environment.volume_name)

    # Update environment with container ID
    environment.is_running = True
    environment.container_id = 'test_container'
    environment.save()

    # Test volume removal
    response = authenticated_client.delete(reverse('environment_delete', kwargs={'pk': environment.pk}))
    assert response.status_code == 302
    mock_volume.remove.assert_called_once()

def test_docker_client_connection_error(mocker):
    """Test handling of Docker client connection errors."""
    mocker.patch('docker.from_env', side_effect=APIError('Connection error'))
    with pytest.raises(APIError):
        from environments.views import get_docker_client
        client = get_docker_client()
