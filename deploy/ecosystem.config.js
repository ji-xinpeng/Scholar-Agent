module.exports = {
  apps: [
    {
      name: 'scholar-backend',
      script: 'server.py',
      cwd: '/path/to/backend',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'scholar-frontend',
      script: 'npm',
      args: 'start',
      cwd: '/path/to/frontend',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
