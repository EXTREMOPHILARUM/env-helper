$(document).ready(function() {
    // Handle environment variables input
    function parseEnvVars(text) {
        const vars = {};
        text.split('\n').forEach(line => {
            line = line.trim();
            if (line) {
                const [key, ...values] = line.split('=');
                vars[key.trim()] = values.join('=').trim();
            }
        });
        return vars;
    }

    function stringifyEnvVars(vars) {
        return Object.entries(vars)
            .map(([key, value]) => `${key}=${value}`)
            .join('\n');
    }

    // Convert environment variables on form submit
    $('form').submit(function(e) {
        const envVarsText = $('#id_environment_variables').val();
        const envVarsJson = JSON.stringify(parseEnvVars(envVarsText));
        
        // Create hidden input for the JSON data
        $('<input>')
            .attr('type', 'hidden')
            .attr('name', 'environment_variables_json')
            .val(envVarsJson)
            .appendTo($(this));
    });

    // Set default images and ports based on environment type
    $('#id_environment_type').change(function() {
        const type = $(this).val();
        if (type === 'vscode') {
            $('#id_image').val('codercom/code-server:latest');
            $('#id_port').val('8443');
            // Set default environment variables for VSCode
            const defaultVars = {
                'PASSWORD': 'your-password-here',
                'DOCKER_USER': '$USER'
            };
            $('#id_environment_variables').val(stringifyEnvVars(defaultVars));
        } else if (type === 'webtop') {
            $('#id_image').val('linuxserver/webtop:ubuntu-kde');
            $('#id_port').val('3000');
            // Set default environment variables for Webtop
            const defaultVars = {
                'PUID': '1000',
                'PGID': '1000',
                'TZ': 'UTC'
            };
            $('#id_environment_variables').val(stringifyEnvVars(defaultVars));
        }
    });
});
