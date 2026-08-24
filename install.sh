#!/bin/bash

# VexPanel Installation & Management Script
# Usage: ./install.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"

# ASCII Art
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
   _____ _     _           _        _____           _     
  / ____| |   (_)         | |      / ____|         | |    
 | (___ | |__  _ _ __   __| | ___ | (___  _ __ __ _| |__  
  \___ \| '_ \| | '_ \ / _` |/ _ \ \___ \| '__/ _` | '_ \ 
  ____) | | | | | | | | (_| |  __/ ____) | | | (_| | |_) |
 |_____/|_| |_|_|_| |_|\__,_|\___| |_____/|_|  \__,_|_.__/ 
                                                           
       VPS & Browser RDP Hosting Panel
EOF
    echo -e "${NC}"
}

# Print functions
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing=()
    
    command -v docker >/dev/null 2>&1 || missing+=("docker")
    command -v docker-compose >/dev/null 2>&1 || missing+=("docker-compose")
    
    if [ ${#missing[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing[*]}"
        print_info "Please install Docker and Docker Compose first"
        return 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running"
        return 1
    fi
    
    print_success "All prerequisites met"
    return 0
}

# Setup environment file
setup_env() {
    if [ ! -f "$ENV_FILE" ]; then
        print_info "Creating .env from template..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        
        # Generate secure secret key
        SECRET_KEY=$(openssl rand -base64 32 2>/dev/null || head -c 32 /dev/urandom | base64)
        sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$ENV_FILE"
        
        # Generate postgres password
        PG_PASSWORD=$(openssl rand -base64 16 2>/dev/null || head -c 16 /dev/urandom | base64)
        sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$PG_PASSWORD|" "$ENV_FILE"
        sed -i "s|POSTGRES_PASSWORD:-change_me|POSTGRES_PASSWORD:-$PG_PASSWORD|" "$ENV_FILE"
        
        print_success "Environment file created with generated secrets"
        print_warning "Please review and edit $ENV_FILE before starting"
        return 1
    fi
    return 0
}

# Install function
do_install() {
    print_info "Starting VexPanel installation..."
    
    check_prerequisites || return 1
    setup_env || return 1
    
    print_info "Building and starting containers..."
    cd "$PROJECT_DIR"
    
    # Build images
    docker-compose build --no-cache
    
    # Start database and redis first
    docker-compose up -d postgres redis
    
    # Wait for database
    print_info "Waiting for database to be ready..."
    sleep 10
    
    # Run migrations
    print_info "Running database migrations..."
    docker-compose run --rm backend alembic upgrade head
    
    # Start all services
    print_info "Starting all services..."
    docker-compose up -d
    
    print_success "VexPanel installed successfully!"
    print_info "Access the panel at: http://localhost:3000"
    print_info "API documentation at: http://localhost:8000/docs"
    print_warning "First run: Create your super admin account at http://localhost:3000/setup"
}

# Uninstall function
do_uninstall() {
    print_warning "This will remove all VexPanel containers, volumes, and data!"
    read -p "Are you sure? Type 'yes' to confirm: " confirm
    
    if [ "$confirm" != "yes" ]; then
        print_info "Uninstall cancelled"
        return 0
    fi
    
    print_info "Stopping and removing containers..."
    cd "$PROJECT_DIR"
    docker-compose down -v --remove-orphans
    
    print_info "Removing images..."
    docker-compose down --rmi all 2>/dev/null || true
    
    print_info "Removing volumes..."
    docker volume rm vexpanel_postgres_data vexpanel_redis_data vexpanel_vexpanel-volumes 2>/dev/null || true
    
    print_success "VexPanel uninstalled completely"
}

# Backup function
do_backup() {
    print_info "Creating backup..."
    
    BACKUP_DIR="$PROJECT_DIR/backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/vexpanel_backup_$TIMESTAMP.tar.gz"
    
    mkdir -p "$BACKUP_DIR"
    
    cd "$PROJECT_DIR"
    
    # Backup database
    print_info "Backing up database..."
    docker-compose exec -T postgres pg_dump -U vexpanel vexpanel > "$BACKUP_DIR/db_$TIMESTAMP.sql"
    
    # Backup volumes
    print_info "Backing up volumes..."
    docker run --rm -v vexpanel_vexpanel-volumes:/data -v "$BACKUP_DIR":/backup alpine tar czf "/backup/volumes_$TIMESTAMP.tar.gz" -C /data .
    
    # Backup config
    tar czf "$BACKUP_FILE" -C "$PROJECT_DIR" .env docker-compose.yml nginx/ 2>/dev/null
    
    print_success "Backup created: $BACKUP_FILE"
    print_info "Database backup: $BACKUP_DIR/db_$TIMESTAMP.sql"
    print_info "Volumes backup: $BACKUP_DIR/volumes_$TIMESTAMP.tar.gz"
}

# Restore function
do_restore() {
    print_warning "This will restore from backup and overwrite current data!"
    
    BACKUP_DIR="$PROJECT_DIR/backups"
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A $BACKUP_DIR)" ]; then
        print_error "No backups found in $BACKUP_DIR"
        return 1
    fi
    
    echo "Available backups:"
    ls -1 "$BACKUP_DIR"/vexpanel_backup_*.tar.gz 2>/dev/null | nl
    
    read -p "Enter backup number to restore: " selection
    BACKUP_FILE=$(ls -1 "$BACKUP_DIR"/vexpanel_backup_*.tar.gz 2>/dev/null | sed -n "${selection}p")
    
    if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
        print_error "Invalid selection"
        return 1
    fi
    
    read -p "Type 'yes' to confirm restore: " confirm
    if [ "$confirm" != "yes" ]; then
        print_info "Restore cancelled"
        return 0
    fi
    
    print_info "Restoring from $BACKUP_FILE..."
    
    cd "$PROJECT_DIR"
    docker-compose down -v
    
    # Restore config
    tar xzf "$BACKUP_FILE" -C "$PROJECT_DIR"
    
    # Restore database
    DB_BACKUP=$(echo "$BACKUP_FILE" | sed 's/vexpanel_backup_/db_/; s/\.tar\.gz/.sql/')
    if [ -f "$DB_BACKUP" ]; then
        docker-compose up -d postgres
        sleep 10
        docker-compose exec -T postgres psql -U vexpanel -d vexpanel < "$DB_BACKUP"
    fi
    
    # Restore volumes
    VOL_BACKUP=$(echo "$BACKUP_FILE" | sed 's/vexpanel_backup_/volumes_/; s/\.tar\.gz/.tar\.gz/')
    if [ -f "$VOL_BACKUP" ]; then
        docker run --rm -v vexpanel_vexpanel-volumes:/data -v "$BACKUP_DIR":/backup alpine tar xzf "/backup/$(basename $VOL_BACKUP)" -C /data
    fi
    
    docker-compose up -d
    print_success "Restore completed"
}

# VPS Manager
do_vps_manager() {
    while true; do
        show_banner
        echo -e "${CYAN}=== VPS Manager ===${NC}"
        echo "1) List all VPS"
        echo "2) Create VPS"
        echo "3) Start VPS"
        echo "4) Stop VPS"
        echo "5) Restart VPS"
        echo "6) Delete VPS"
        echo "7) VPS Console"
        echo "8) VPS Metrics"
        echo "9) Back to main menu"
        echo ""
        read -p "Select option [1-9]: " choice
        
        case $choice in
            1) vps_list ;;
            2) vps_create ;;
            3) vps_action "start" ;;
            4) vps_action "stop" ;;
            5) vps_action "restart" ;;
            6) vps_action "delete" ;;
            7) vps_console ;;
            8) vps_metrics ;;
            9) return ;;
            *) print_error "Invalid option" ;;
        esac
        read -p "Press Enter to continue..."
    done
}

vps_list() {
    print_info "Fetching VPS list..."
    docker-compose exec backend python -c "
from app.database.session import get_db_context
from app.models import VPSInstance
with get_db_context() as db:
    vps_list = db.query(VPSInstance).all()
    for v in vps_list:
        print(f'{v.id:3} | {v.vps_id:12} | {v.status.value:12} | {v.cpu}vCPU/{v.ram}GB/{v.storage}GB | {v.ipv4 or \"pending\":15} | {v.hostname}')
"
}

vps_create() {
    echo "Create new VPS"
    read -p "Hostname: " hostname
    read -p "CPU cores: " cpu
    read -p "RAM (GB): " ram
    read -p "Storage (GB): " storage
    read -p "OS Image (default ubuntu:22.04): " os_image
    os_image=${os_image:-ubuntu:22.04}
    
    docker-compose exec backend python -c "
from app.database.session import get_db_context
from app.providers import get_vps_provider
from app.providers.interface import VPSConfig
import asyncio, uuid

async def create():
    config = VPSConfig(cpu=$cpu, ram=$ram, storage=$storage, os_image='$os_image', hostname='$hostname')
    provider = get_vps_provider()
    result = await provider.create_vps(config, 1)
    print(f'VPS created: {result.vps_id} (Provider ID: {result.provider_id})')

asyncio.run(create())
"
}

vps_action() {
    local action=$1
    read -p "Enter VPS ID: " vps_id
    
    docker-compose exec backend python -c "
from app.database.session import get_db_context
from app.models import VPSInstance
from app.providers import get_vps_provider
import asyncio

async def action():
    with get_db_context() as db:
        vps = db.query(VPSInstance).filter(VPSInstance.id == $vps_id).first()
        if not vps:
            print('VPS not found')
            return
        provider = get_vps_provider()
        if '$action' == 'start':
            await provider.start_vps(vps.provider_id)
        elif '$action' == 'stop':
            await provider.stop_vps(vps.provider_id)
        elif '$action' == 'restart':
            await provider.restart_vps(vps.provider_id)
        elif '$action' == 'delete':
            await provider.delete_vps(vps.provider_id)
            db.delete(vps)
        print(f'VPS \$action completed')

asyncio.run(action())
"
}

vps_console() {
    read -p "Enter VPS ID: " vps_id
    print_info "Opening console for VPS $vps_id..."
    print_info "Use Ctrl+] to exit"
    docker-compose exec -it backend python -c "
from app.database.session import get_db_context
from app.models import VPSInstance
from app.providers import get_vps_provider
import asyncio

async def console():
    with get_db_context() as db:
        vps = db.query(VPSInstance).filter(VPSInstance.id == $vps_id).first()
        if vps:
            provider = get_vps_provider()
            import docker
            client = docker.from_env()
            container = client.containers.get(vps.container_id)
            import sys, os, pty
            # This would need a proper terminal implementation
            print('Console access via: docker exec -it', vps.container_id, '/bin/bash')

asyncio.run(console())
"
}

vps_metrics() {
    read -p "Enter VPS ID: " vps_id
    
    docker-compose exec backend python -c "
from app.database.session import get_db_context
from app.models import VPSInstance
from app.providers import get_vps_provider
import asyncio

async def metrics():
    with get_db_context() as db:
        vps = db.query(VPSInstance).filter(VPSInstance.id == $vps_id).first()
        if vps:
            provider = get_vps_provider()
            m = await provider.get_vps_metrics(vps.provider_id)
            print(f'CPU: {m.cpu_percent}%')
            print(f'Memory: {m.memory_percent}%')
            print(f'Disk: {m.disk_percent}%')
            print(f'Net In: {m.network_in_bytes/1024/1024:.2f} MB')
            print(f'Net Out: {m.network_out_bytes/1024/1024:.2f} MB')

asyncio.run(metrics())
"
}

# Restart services
do_restart() {
    print_info "Restarting services..."
    cd "$PROJECT_DIR"
    
    echo "Select service to restart:"
    echo "1) All services"
    echo "2) Backend only"
    echo "3) Frontend only"
    echo "4) Worker only"
    echo "5) Database only"
    echo "6) Redis only"
    read -p "Choice [1-6]: " choice
    
    case $choice in
        1) docker-compose restart ;;
        2) docker-compose restart backend ;;
        3) docker-compose restart frontend ;;
        4) docker-compose restart worker ;;
        5) docker-compose restart postgres ;;
        6) docker-compose restart redis ;;
        *) print_error "Invalid choice" ;;
    esac
    
    print_success "Services restarted"
}

# Start services
do_start() {
    echo -e "${CYAN}=== Start Services ===${NC}"
    echo "1) Start Backend (API + Worker)"
    echo "2) Start Frontend"
    echo "3) Start All Services"
    echo "4) Back to main menu"
    read -p "Select option [1-4]: " choice
    
    cd "$PROJECT_DIR"
    
    case $choice in
        1)
            print_info "Starting backend services..."
            docker-compose up -d postgres redis backend worker
            print_success "Backend started"
            ;;
        2)
            print_info "Starting frontend..."
            docker-compose up -d frontend nginx
            print_success "Frontend started"
            ;;
        3)
            print_info "Starting all services..."
            docker-compose up -d
            print_success "All services started"
            ;;
        4) return ;;
        *) print_error "Invalid option" ;;
    esac
}

# Stop services
do_stop() {
    print_info "Stopping all services..."
    cd "$PROJECT_DIR"
    docker-compose down
    print_success "All services stopped"
}

# Show logs
do_logs() {
    echo "Select service to view logs:"
    echo "1) All services"
    echo "2) Backend"
    echo "3) Frontend"
    echo "4) Worker"
    echo "4) Database"
    echo "5) Nginx"
    read -p "Choice [1-5]: " choice
    
    cd "$PROJECT_DIR"
    
    case $choice in
        1) docker-compose logs -f --tail=100 ;;
        2) docker-compose logs -f --tail=100 backend ;;
        3) docker-compose logs -f --tail=100 frontend ;;
        4) docker-compose logs -f --tail=100 worker ;;
        5) docker-compose logs -f --tail=100 postgres ;;
        6) docker-compose logs -f --tail=100 nginx ;;
        *) print_error "Invalid choice" ;;
    esac
}

# Show status
do_status() {
    print_info "Service Status:"
    cd "$PROJECT_DIR"
    docker-compose ps
    
    echo ""
    print_info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# Main menu
show_menu() {
    show_banner
    echo -e "${CYAN}=== VexPanel Management Menu ===${NC}"
    echo -e "  ${GREEN}1)${NC} Install VexPanel"
    echo -e "  ${GREEN}2)${NC} Uninstall VexPanel"
    echo -e "  ${GREEN}3)${NC} Backup VexPanel"
    echo -e "  ${GREEN}4)${NC} Restore from Backup"
    echo -e "  ${GREEN}5)${NC} VPS Manager"
    echo -e "  ${GREEN}6)${NC} Restart Services"
    echo -e "  ${GREEN}7)${NC} Start Services (Backend/Frontend)"
    echo -e "  ${GREEN}8)${NC} Stop All Services"
    echo -e "  ${GREEN}9)${NC} View Logs"
    echo -e "  ${GREEN}10)${NC} Show Status"
    echo -e "  ${GREEN}11)${NC} Edit Environment (.env)"
    echo -e "  ${GREEN}12)${NC} Exit"
    echo ""
}

# Edit env file
edit_env() {
    ${EDITOR:-nano} "$ENV_FILE"
}

# Main loop
main() {
    while true; do
        show_menu
        read -p "Select option [1-12]: " choice
        
        case $choice in
            1) do_install ;;
            2) do_uninstall ;;
            3) do_backup ;;
            4) do_restore ;;
            5) do_vps_manager ;;
            6) do_restart ;;
            7) do_start ;;
            8) do_stop ;;
            9) do_logs ;;
            10) do_status ;;
            11) edit_env ;;
            12) 
                print_info "Goodbye!"
                exit 0 
                ;;
            *) print_error "Invalid option. Please select 1-12." ;;
        esac
        echo ""
    done
}

# Run main
main "$@"