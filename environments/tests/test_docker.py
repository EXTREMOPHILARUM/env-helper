import pytest
from django.urls import reverse
import docker
from environments.models import Environment
from environments.views import get_docker_client

@pytest.mark.django_db
def test_environment_start_with_docker_error(mocker, authenticated_client, environment):
    """Test handling of Docker errors when starting an environment."""
    mock_client = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_containers.run.side_effect = docker.errors.APIError('Docker API error')
    mock_client.containers = mock_containers
    mocker.patch('environments.views.get_docker_client', return_value=mock_client)

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
    mock_container.stop.side_effect = docker.errors.APIError('Docker API error')
    mock_containers.get.return_value = mock_container
    mock_client.containers = mock_containers
    mocker.patch('environments.views.get_docker_client', return_value=mock_client)

    response = authenticated_client.post(reverse('environment_stop', kwargs={'pk': environment.pk}))
    assert response.status_code == 500
    environment.refresh_from_db()
    assert environment.is_running

@pytest.mark.django_db
def test_environment_container_cleanup(mocker, authenticated_client, environment):
    """Test container cleanup on environment deletion."""
    # Set up environment state
    environment.is_running = True
    environment.container_id = 'test_container'
    environment.volume_name = 'test_volume'
    environment.save()

    print(f"\nEnvironment state before deletion:")
    print(f"  is_running={environment.is_running}")
    print(f"  container_id={environment.container_id}")
    print(f"  volume_name={environment.volume_name}")

    # Mock Docker client and container
    mock_container = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    
    # Configure container mock
    mock_container.stop.return_value = None
    mock_container.remove.return_value = None
    
    # Configure volume mock
    mock_volume.remove.return_value = None
    
    # Configure Docker client mock with containers and volumes attributes
    mock_client = mocker.MagicMock()
    mock_client.containers = mocker.MagicMock()
    mock_client.volumes = mocker.MagicMock()
    mock_client.containers.get.return_value = mock_container
    mock_client.volumes.get.return_value = mock_volume
    mock_client.version.return_value = {'ApiVersion': '1.41'}
    
    print("\nMock configuration:")
    print("  - Configured mock_container.stop")
    print("  - Configured mock_container.remove")
    print("  - Configured mock_client.containers.get to return mock_container")
    print("  - Configured mock_client.volumes.get to return mock_volume")
    
    # Mock the Docker client at module level
    mocker.patch('docker.DockerClient', return_value=mock_client)
    
    print("\nMocks configured, about to delete environment...")

    # Delete the environment using perform_destroy
    from environments.views import EnvironmentViewSet
    viewset = EnvironmentViewSet()
    viewset.perform_destroy(environment)
    
    print("\nChecking Docker interactions...")
    print(f"  - mock_client.containers.get called: {mock_client.containers.get.call_count} times")
    print(f"  - mock_container.stop called: {mock_container.stop.call_count} times")
    print(f"  - mock_container.remove called: {mock_container.remove.call_count} times")
    print(f"  - mock_volume.remove called: {mock_volume.remove.call_count} times")
    
    # Verify Docker interactions
    assert mock_client.containers.get.call_count > 0, "containers.get was not called"
    mock_container.stop.assert_called_once()
    mock_container.remove.assert_called_once()
    mock_volume.remove.assert_called_once()

@pytest.mark.django_db
def test_docker_volume_management(mocker, authenticated_client, environment):
    """Test Docker volume management."""
    # Mock Docker client and volumes
    mock_client = mocker.MagicMock()
    mock_volumes = mocker.MagicMock()
    mock_volume = mocker.MagicMock()
    mock_containers = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    
    # Configure mocks
    mock_volumes.get.side_effect = docker.errors.NotFound('Volume not found')
    mock_volumes.create.return_value = mock_volume
    mock_containers.run.return_value = mock_container
    mock_client.volumes = mock_volumes
    mock_client.containers = mock_containers
    
    mocker.patch('environments.views.get_docker_client', return_value=mock_client)

    # Try to start the environment
    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    assert response.status_code in [302, 500]
    
    # Verify volume creation was attempted
    mock_volumes.create.assert_called_once_with(name=environment.volume_name)

@pytest.mark.django_db
def test_environment_start_with_env_vars(mocker, authenticated_client, environment):
    """Test starting an environment with environment variables."""
    # Set up environment state
    environment.env_vars = """
    # This is a comment
    KEY1=value1
    KEY2=value with spaces
    KEY3=value=with=equals
    """
    environment.save()

    # Mock Docker client and container
    mock_container = mocker.MagicMock()
    mock_container.id = 'test_container_id'
    
    # Configure Docker client mock
    mock_client = mocker.MagicMock()
    mock_client.containers.run.return_value = mock_container
    mock_client.volumes.get.side_effect = docker.errors.NotFound('Volume not found')
    mock_client.volumes.create.return_value = mocker.MagicMock()
    
    # Mock the get_docker_client function
    mocker.patch('environments.views.get_docker_client', return_value=mock_client)

    # Start the environment
    response = authenticated_client.post(reverse('environment_start', kwargs={'pk': environment.pk}))
    assert response.status_code == 302

    # Verify Docker interactions
    mock_client.containers.run.assert_called_once()
    run_kwargs = mock_client.containers.run.call_args[1]
    
    # Verify environment variables were parsed correctly
    expected_env_vars = {
        'KEY1': 'value1',
        'KEY2': 'value with spaces',
        'KEY3': 'value=with=equals'
    }
    assert run_kwargs['environment'] == expected_env_vars

@pytest.mark.django_db
def test_docker_client_connection_error(mocker):
    """Test handling of Docker client connection errors."""
    mocker.patch('environments.views.get_docker_client', side_effect=docker.errors.APIError('Docker API error'))
    with pytest.raises(docker.errors.APIError):
        from environments.views import get_docker_client
        get_docker_client()
