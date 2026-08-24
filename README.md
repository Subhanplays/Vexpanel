# VexPanel - VPS & Browser RDP Hosting Panel

A production-ready VPS management panel with browser-accessible RDP desktop hosting.

## Features

- **VPS Management**: Create, start, stop, restart, rebuild, delete VPS instances
- **Resource Monitoring**: Real-time CPU, RAM, disk, and network metrics
- **Browser RDP**: Ubuntu desktop in Docker on user's VPS, accessible via TryCloudflare or Pinggy tunnels
- **Web Terminal**: Browser-based SSH terminal for VPS management
- **Admin Panel**: Complete user, VPS, RDP, host, and system management
- **Role-Based Access Control**: Super Admin, Admin, Support, Read Only, User roles
- **Background Jobs**: Async job queue for all provisioning operations
- **Audit Logging**: Comprehensive activity tracking
- **Multi-Provider Architecture**: Extensible VPS and tunnel provider abstractions

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│  Backend    │────▶│  Database   │
│  (React)    │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Worker    │
                    │  (Async)    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │ VPS       │    │ RDP       │    │ Tunnel    │
    │ Provider  │    │ Manager   │    │ Manager   │
    └───────────┘    └───────────┘    └───────────┘
          │                │                │
          ▼                ▼                ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │ Docker    │    │ Docker on │    │ TryCloud- │
    │ Containers│    │ User VPS  │    │flare/Pinggy
    └───────────┘    └───────────┘    └───────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 16+ (or use included container)
- Redis 7+ (or use included container)

### Development

```bash
# Clone and navigate
cd VexPanel

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Access frontend at http://localhost:3000
# Access API docs at http://localhost:8000/docs
```

### Production Deployment

1. **Configure environment variables** in `.env`:
   ```bash
   SECRET_KEY=generate-secure-random-string
   DATABASE_URL=postgresql://user:pass@host:5432/vexpanel
   REDIS_URL=redis://host:6379/0
   VPS_PROVIDER=custom
   PINGGY_TOKEN=your-pinggy-token  # optional
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Run migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Setup reverse proxy** (nginx/Traefik) with SSL

5. **First run**: Navigate to your domain and create the super admin account

## Project Structure

```
VexPanel/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── auth/           # Authentication & RBAC
│   │   ├── core/           # Configuration
│   │   ├── database/       # Database session
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   ├── providers/      # VPS provider abstraction
│   │   ├── rdp/            # RDP management
│   │   ├── tunnels/        # Tunnel providers
│   │   ├── jobs/           # Background job queue
│   │   └── main.py         # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React frontend
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── hooks/          # React hooks
│   │   ├── utils/          # Utilities
│   │   └── types/          # TypeScript types
│   ├── Dockerfile
│   └── nginx.conf
├── migrations/             # Alembic migrations
├── workers/                # Background workers
├── nginx/                  # Reverse proxy config
├── docker-compose.yml
└── .env.example
```

## RDP Workflow

1. User creates VPS instance
2. VPS becomes ready (running)
3. User opens VPS dashboard → RDP tab
4. User clicks "Create RDP"
5. System provisions Docker desktop on **user's VPS** (port 6080)
6. User selects tunnel provider: TryCloudflare or Pinggy
7. Tunnel created → public URL generated
8. User clicks "Open RDP" → browser desktop

**Key Design**: Each VPS runs its own RDP container on port 6080. No port conflicts since they're on different machines.

## Provider Abstraction

The VPS provider interface allows swapping implementations:

```python
class VPSProvider(ABC):
    async def create_vps(self, config: VPSConfig, user_id: int) -> VPSInfo
    async def delete_vps(self, provider_id: str) -> bool
    async def start_vps(self, provider_id: str) -> bool
    async def stop_vps(self, provider_id: str) -> bool
    async def restart_vps(self, provider_id: str) -> bool
    async def rebuild_vps(self, provider_id: str, os_image: str) -> bool
    async def get_vps(self, provider_id: str) -> Optional[VPSInfo]
    async def get_vps_status(self, provider_id: str) -> VPSPowerState
    async def get_vps_metrics(self, provider_id: str) -> VPSMetrics
    async def execute_command(self, provider_id: str, command: str) -> CommandResult
    async def open_console(self, provider_id: str) -> Dict[str, Any]
```

Built-in providers:
- `CustomVPSProvider` - Uses Docker on local host (from hvm.py)
- `MockVPSProvider` - For development/testing

## Tunnel Providers

- **TryCloudflare**: Free Cloudflare Quick Tunnels (`cloudflared`)
- **Pinggy**: SSH-based tunnels (`ssh -R`)

Both automatically capture the public URL and update the database.

## API Endpoints

### VPS Management
```
GET    /api/v1/vps                    # List user's VPS
POST   /api/v1/vps                    # Create VPS
GET    /api/v1/vps/{id}               # Get VPS details
PUT    /api/v1/vps/{id}               # Update VPS
POST   /api/v1/vps/{id}/start         # Start VPS
POST   /api/v1/vps/{id}/stop          # Stop VPS
POST   /api/v1/vps/{id}/restart       # Restart VPS
POST   /api/v1/vps/{id}/rebuild       # Rebuild VPS
DELETE /api/v1/vps/{id}               # Delete VPS
GET    /api/v1/vps/{id}/metrics       # Get metrics
POST   /api/v1/vps/{id}/command       # Execute command (admin)
```

### RDP Management
```
GET    /api/v1/vps/{id}/rdp           # Get RDP status
POST   /api/v1/vps/{id}/rdp           # Create RDP
POST   /api/v1/vps/{id}/rdp/tunnel    # Create tunnel
POST   /api/v1/vps/{id}/rdp/tunnel/change  # Change provider
POST   /api/v1/vps/{id}/rdp/restart   # Restart RDP
POST   /api/v1/vps/{id}/rdp/stop      # Stop RDP
DELETE /api/v1/vps/{id}/rdp           # Delete RDP
GET    /api/v1/vps/{id}/rdp/logs      # Get container logs
```

### Admin
```
GET    /api/v1/admin/dashboard        # Dashboard stats
GET    /api/v1/admin/users            # List users
POST   /api/v1/admin/users            # Create user
PUT    /api/v1/admin/users/{id}       # Update user
DELETE /api/v1/admin/users/{id}       # Delete user
GET    /api/v1/admin/vps              # List all VPS
GET    /api/v1/admin/rdp              # List all RDP
GET    /api/v1/admin/audit-logs       # Audit logs
GET    /api/v1/admin/jobs             # Job queue
GET    /api/v1/admin/plans            # VPS plans
POST   /api/v1/admin/plans            # Create plan
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | Required |
| `DATABASE_URL` | PostgreSQL connection | sqlite:///./vexpanel.db |
| `REDIS_URL` | Redis connection | redis://localhost:6379/0 |
| `VPS_PROVIDER` | Provider type: `custom` or `mock` | custom |
| `PINGGY_TOKEN` | Pinggy authentication token | Optional |
| `MAX_VPS_PER_USER` | VPS limit per user | 3 |
| `DEFAULT_OS_IMAGE` | Default Docker image | ubuntu:22.04 |
| `RDP_DOCKER_IMAGE` | RDP desktop image | akarita/docker-ubuntu-desktop |
| `RDP_INTERNAL_PORT` | RDP port inside VPS | 6080 |

## Security

- Argon2id password hashing
- JWT authentication with secure cookies
- Role-based access control (RBAC)
- Rate limiting on auth endpoints
- Input validation with Pydantic
- SQL injection protection via SQLAlchemy ORM
- WebSocket authentication
- Audit logging for all actions

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## License

MIT License - see LICENSE file for details.