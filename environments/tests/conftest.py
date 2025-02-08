import pytest
from django.contrib.auth.models import User
from django.test import Client
from environments.models import Environment

@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='testpass123')

@pytest.fixture
def authenticated_client(user):
    client = Client()
    client.login(username='testuser', password='testpass123')
    return client

@pytest.fixture
def environment(user):
    return Environment.objects.create(
        name='test-env',
        description='Test Environment',
        environment_type='vscode',
        image='python:3.11-slim',
        ports='8080:80',
        created_by=user,
        environment_variables={'PUID': '1000', 'PGID': '1000', 'TZ': 'UTC'}
    )

@pytest.fixture
def mock_docker_client(mocker):
    mock_client = mocker.MagicMock()
    mock_client.containers.run.return_value = mocker.MagicMock(id='test_container_id')
    mock_client.containers.get.return_value = mocker.MagicMock(status='running')
    return mock_client
