import multiprocessing

# The socket to bind
bind = "0.0.0.0:5000"

# The number of worker processes
workers = multiprocessing.cpu_count() * 2 + 1

# The type of workers to use
worker_class = 'sync'

# The maximum number of simultaneous clients
worker_connections = 1000

# The maximum number of requests a worker will process before restarting
max_requests = 1000

# The maximum jitter to add to the max_requests setting
max_requests_jitter = 50

# Timeout for graceful workers restart
graceful_timeout = 30

# Timeout for worker processes
timeout = 30

# The number of seconds to wait for requests on a Keep-Alive connection
keepalive = 2

# Log level
loglevel = 'info'
