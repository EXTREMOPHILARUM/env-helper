from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
import docker
from docker.errors import APIError, NotFound
import os
import logging
import socket
from django.http import JsonResponse

from .models import Environment
from .serializers import EnvironmentSerializer
from .forms import EnvironmentForm

# Set up logger
logger = logging.getLogger(__name__)

def get_docker_client():
    """Create a Docker client using the Unix socket."""
    try:
        logger.info("Initializing Docker client with unix:///var/run/docker.sock")
        client = docker.DockerClient(base_url='unix:///var/run/docker.sock')
        # Test the connection
        version = client.version()
        logger.info(f"Successfully connected to Docker daemon (API Version: {version.get('ApiVersion')})")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Docker client: {str(e)}", exc_info=True)
        raise

def check_port_available(request):
    """Check if a port is available on the host system."""
    try:
        port = int(request.GET.get('port', 0))
        if not 1 <= port <= 65535:
            return JsonResponse({'available': False, 'error': 'Port must be between 1 and 65535'})

        # Check if port is in use by other environments
        if Environment.objects.filter(ports__contains=f"{port}:").exists():
            return JsonResponse({
                'available': False, 
                'error': f'Port {port} is already in use by another environment'
            })

        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()

        if result == 0:
            return JsonResponse({
                'available': False, 
                'error': f'Port {port} is already in use by another application'
            })
        return JsonResponse({'available': True})

    except ValueError:
        return JsonResponse({'available': False, 'error': 'Invalid port number'})
    except Exception as e:
        return JsonResponse({'available': False, 'error': str(e)})

class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    
    def perform_create(self, serializer):
        logger.info(f"Creating new environment for user {self.request.user}")
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        return Environment.objects.filter(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a Docker container for the environment."""
        environment = self.get_object()
        logger.info(f"Attempting to start environment {environment.pk} ({environment.name})")
        
        try:
            client = get_docker_client()
            
            # Check if volume exists, create if not
            volume_name = environment.volume_name
            logger.info(f"Checking for volume {volume_name}")
            try:
                client.volumes.get(volume_name)
                logger.info(f"Volume {volume_name} found")
            except docker.errors.NotFound:
                logger.info(f"Creating volume {volume_name}")
                client.volumes.create(name=volume_name)
            
            # Start container
            logger.info(f"Starting container for environment {environment.pk}")
            container_name = environment.container_name
            
            # Parse ports from the ports string
            ports_list = [p.strip() for p in environment.ports.split(',') if p.strip()]
            port_mappings = {}
            for port_mapping in ports_list:
                if ':' in port_mapping:
                    host_port, container_port = port_mapping.split(':')
                    port_mappings[f'{container_port}/tcp'] = host_port
            
            # Log container configuration
            logger.debug(f"Container config: image={environment.image}, ports={port_mappings}, "
                        f"volume={volume_name}, env_vars={environment.environment_variables}")
            
            try:
                # Get environment variables
                env_vars = {}
                if environment.env_vars:
                    env_vars = {
                        line.split('=', 1)[0].strip(): line.split('=', 1)[1].strip()
                        for line in environment.env_vars.split('\n')
                        if '=' in line and not line.strip().startswith('#')
                    }
                logger.debug(f"Parsed environment variables: {env_vars}")

                # Create and start the container
                container = client.containers.run(
                    environment.image,
                    name=container_name,
                    detach=True,
                    network="env-helper-network",  # Add container to Traefik network
                    volumes={volume_name: {'bind': '/config', 'mode': 'rw'}},
                    environment=env_vars,
                    restart_policy={"Name": "unless-stopped"} if environment.auto_start else {"Name": "no"},
                    labels={
                        "traefik.enable": "true",
                        # Create a router and service for each port
                        **{
                            f"traefik.http.routers.{container_name}-{port_label}.rule": 
                                f"Host(`{environment.subdomain}-{port_label}.{{env.DOMAIN}}`)"
                            for port_label in environment.ports.keys()
                        },
                        **{
                            f"traefik.http.routers.{container_name}-{port_label}.entrypoints": "web"
                            for port_label in environment.ports.keys()
                        },
                        **{
                            f"traefik.http.services.{container_name}-{port_label}.loadbalancer.server.port": port_config['port']
                            for port_label, port_config in environment.ports.items()
                        },
                        # Add TLS configuration for each router
                        **{
                            f"traefik.http.routers.{container_name}-{port_label}.tls": "true"
                            for port_label in environment.ports.keys()
                        },
                        **{
                            f"traefik.http.routers.{container_name}-{port_label}.tls.certresolver": "letsencrypt"
                            for port_label in environment.ports.keys()
                        }
                    }
                )
                logger.info(f"Container {container.id} started successfully")
                
                # Update environment
                environment.container_id = container.id
                environment.is_running = True
                environment.save()
                logger.info(f"Environment {environment.pk} updated with container ID {container.id}")
                
                messages.success(request, f'Environment "{environment.name}" started successfully')
                return redirect('environment_list')
            except docker.errors.APIError as e:
                logger.error(f"Failed to start container: {str(e)}")
                messages.error(request, f'Failed to start environment: {str(e)}')
                return render(request, 'environments/environment_list.html', status=500)
                
        except Exception as e:
            logger.error(f"Failed to start environment {environment.pk}: {str(e)}", exc_info=True)
            messages.error(request, f'Failed to start environment: {str(e)}')
            return render(request, 'environments/environment_list.html', status=500)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a Docker container for the environment."""
        environment = self.get_object()
        logger.info(f"Attempting to stop environment {environment.pk} ({environment.name})")
        
        if not environment.is_running:
            logger.warning(f"Environment {environment.pk} is not running")
            messages.warning(request, 'Environment is not running')
            return redirect('environment_list')
        
        try:
            client = get_docker_client()
            container_id = environment.container_id
            logger.info(f"Getting container {container_id}")
            
            try:
                client.containers.get(container_id).stop()
                logger.info(f"Container {container_id} stopped successfully")
                client.containers.get(container_id).remove()
                logger.info(f"Container {container_id} removed successfully")
                
                # Update environment
                environment.container_id = None
                environment.is_running = False
                environment.save()
                logger.info(f"Environment {environment.pk} updated")
                
                messages.success(request, f'Environment "{environment.name}" stopped successfully')
                return redirect('environment_list')
            except docker.errors.APIError as e:
                logger.error(f"Failed to stop container: {str(e)}")
                messages.error(request, f'Failed to stop environment: {str(e)}')
                return render(request, 'environments/environment_list.html', status=500)
                
        except Exception as e:
            logger.error(f"Failed to stop environment {environment.pk}: {str(e)}", exc_info=True)
            messages.error(request, f'Failed to stop environment: {str(e)}')
            return render(request, 'environments/environment_list.html', status=500)
    
    def perform_destroy(self, instance):
        logger.info(f"Destroying environment {instance.id} ({instance.name})")
        
        try:
            client = get_docker_client()
            
            # Stop and remove container if running
            if instance.is_running and instance.container_id:
                try:
                    logger.info(f"Stopping container {instance.container_id[:12]}")
                    client.containers.get(instance.container_id).stop()
                    logger.info(f"Container {instance.container_id[:12]} stopped successfully")
                    client.containers.get(instance.container_id).remove()
                    logger.info(f"Container {instance.container_id[:12]} removed successfully")
                except docker.errors.NotFound:
                    logger.warning(f"Container {instance.container_id[:12]} not found")
            
            # Remove volume
            try:
                logger.info(f"Removing volume {instance.volume_name}")
                client.volumes.get(instance.volume_name).remove()
                logger.info(f"Volume {instance.volume_name} removed")
            except docker.errors.NotFound:
                logger.warning(f"Volume {instance.volume_name} not found")
            
            super().perform_destroy(instance)
            logger.info(f"Environment {instance.id} destroyed successfully")
            
        except Exception as e:
            logger.error(f"Failed to destroy environment {instance.id}: {str(e)}", exc_info=True)
            raise

class EnvironmentListView(LoginRequiredMixin, ListView):
    model = Environment
    template_name = 'environments/environment_list.html'
    context_object_name = 'environments'

    def get_queryset(self):
        logger.debug(f"Fetching environments for user {self.request.user}")
        return Environment.objects.filter(created_by=self.request.user)

class EnvironmentDetailView(LoginRequiredMixin, DetailView):
    model = Environment
    template_name = 'environments/environment_detail.html'
    context_object_name = 'environment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            logger.debug("Environment vars in view: %s %s", type(self.object.env_vars), self.object.env_vars)
            logger.debug("Environment vars as text: %s", self.object.env_vars_as_text)
        return context

    def get_queryset(self):
        return Environment.objects.filter(created_by=self.request.user)

class EnvironmentCreateView(LoginRequiredMixin, CreateView):
    model = Environment
    template_name = 'environments/environment_form.html'
    form_class = EnvironmentForm
    success_url = reverse_lazy('environment_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['environment'] = None  # Set to None for create view
        return context

    def form_valid(self, form):
        """Set the created_by field to the current user."""
        form.instance.created_by = self.request.user
        
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Environment "{form.instance.name}" created successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Failed to create environment: {str(e)}')
            return self.form_invalid(form)

class EnvironmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Environment
    template_name = 'environments/environment_form.html'
    form_class = EnvironmentForm
    success_url = reverse_lazy('environment_list')

    def get_queryset(self):
        return Environment.objects.filter(created_by=self.request.user)
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, f'Environment "{form.instance.name}" updated successfully.')
            return response
        except Exception as e:
            messages.error(self.request, f'Failed to update environment: {str(e)}')
            return self.form_invalid(form)

class EnvironmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Environment
    success_url = reverse_lazy('environment_list')
    
    def get_queryset(self):
        return Environment.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        environment = self.get_object()
        logger.info(f"Deleting environment {environment.id} ({environment.name})")
        logger.info(f"Environment state: is_running={environment.is_running}, container_id={environment.container_id}")
        
        try:
            client = get_docker_client()
            logger.info("Successfully got Docker client")
            
            # Stop and remove container if running
            if environment.is_running and environment.container_id:
                try:
                    logger.info(f"Stopping container {environment.container_id[:12]}")
                    client.containers.get(environment.container_id).stop()
                    logger.info(f"Container {environment.container_id[:12]} stopped successfully")
                    client.containers.get(environment.container_id).remove()
                    logger.info(f"Container {environment.container_id[:12]} removed successfully")
                except docker.errors.NotFound:
                    logger.warning(f"Container {environment.container_id[:12]} not found")
            
            # Remove all associated volumes
            # First, remove the main volume
            if environment.volume_name:
                try:
                    logger.info(f"Removing main volume {environment.volume_name}")
                    client.volumes.get(environment.volume_name).remove()
                    logger.info(f"Main volume {environment.volume_name} removed")
                except docker.errors.NotFound:
                    logger.warning(f"Main volume {environment.volume_name} not found")
                except docker.errors.APIError as e:
                    logger.error(f"Failed to remove main volume {environment.volume_name}: {str(e)}")

            # Then remove any additional volumes defined in the volumes field
            if environment.volumes:
                for volume_line in environment.volumes.split('\n'):
                    if ':' in volume_line:  # Only process volume mappings
                        volume_name = volume_line.split(':')[0].strip()
                        if volume_name:  # Skip empty lines
                            try:
                                logger.info(f"Removing additional volume {volume_name}")
                                client.volumes.get(volume_name).remove()
                                logger.info(f"Additional volume {volume_name} removed")
                            except docker.errors.NotFound:
                                logger.warning(f"Additional volume {volume_name} not found")
                            except docker.errors.APIError as e:
                                logger.error(f"Failed to remove additional volume {volume_name}: {str(e)}")
            
            # Call super().delete() to delete the environment
            response = super().delete(request, *args, **kwargs)
            messages.success(request, 'Environment and all associated volumes deleted successfully!')
            return response
            
        except docker.errors.APIError as e:
            logger.error(f"Docker API error: {str(e)}")
            messages.error(request, f'Failed to delete environment: {str(e)}')
            return redirect('environment_list')
        except Exception as e:
            logger.error(f"Error during environment cleanup: {str(e)}", exc_info=True)
            messages.error(request, f'Failed to delete environment: {str(e)}')
            return redirect('environment_list')
