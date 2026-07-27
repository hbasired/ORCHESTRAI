#!/bin/bash
# Deployment Script for Google Cloud Run
# AI Embodied Agent Manufacturing Optimization Platform

set -e

# ============================================================================
# Configuration
# ============================================================================
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="ai-embodied-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Pre-flight Checks
# ============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."
    
    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    
    # Check project ID
    if [ "$PROJECT_ID" == "your-project-id" ]; then
        log_error "Please set GCP_PROJECT_ID environment variable."
        exit 1
    fi
    
    log_info "Pre-flight checks passed!"
}

# ============================================================================
# Authenticate with GCP
# ============================================================================
authenticate() {
    log_info "Authenticating with Google Cloud..."
    
    # Check if already authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
        log_info "Already authenticated as: $ACCOUNT"
    else
        gcloud auth login
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    log_info "Authentication complete!"
}

# ============================================================================
# Build Docker Image
# ============================================================================
build_image() {
    log_info "Building Docker image..."
    
    # Navigate to project root
    cd "$(dirname "$0")/.."
    
    # Build image
    docker build \
        -f docker/Dockerfile \
        -t $IMAGE_NAME:latest \
        -t $IMAGE_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "dev") \
        .
    
    log_info "Docker image built successfully!"
}

# ============================================================================
# Push Image to GCR
# ============================================================================
push_image() {
    log_info "Pushing image to Google Container Registry..."
    
    docker push $IMAGE_NAME:latest
    
    log_info "Image pushed successfully!"
}

# ============================================================================
# Deploy to Cloud Run
# ============================================================================
deploy() {
    log_info "Deploying to Google Cloud Run..."
    
    gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_NAME:latest \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 0 \
        --max-instances 3 \
        --port 8080 \
        --timeout 300 \
        --concurrency 80 \
        --set-env-vars "SIMULATION_MODE=true,LOG_LEVEL=INFO" \
        --labels "app=ai-agent,env=production"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region $REGION \
        --format "value(status.url)")
    
    log_info "Deployment complete!"
    log_info "Service URL: $SERVICE_URL"
    
    echo ""
    echo "=========================================="
    echo "  AI Embodied Agent Deployed Successfully"
    echo "=========================================="
    echo "Service URL: $SERVICE_URL"
    echo "Health Check: ${SERVICE_URL}/health"
    echo "API Docs: ${SERVICE_URL}/docs"
    echo "=========================================="
}

# ============================================================================
# Set Environment Variables
# ============================================================================
set_env_vars() {
    log_info "Setting environment variables..."
    
    # Read from .env file if exists
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Set environment variables on Cloud Run
    ENV_VARS=""
    
    if [ -n "$SUPABASE_URL" ]; then
        ENV_VARS="$ENV_VARS,SUPABASE_URL=$SUPABASE_URL"
    fi
    
    if [ -n "$SUPABASE_KEY" ]; then
        ENV_VARS="$ENV_VARS,SUPABASE_KEY=$SUPABASE_KEY"
    fi
    
    if [ -n "$OPENWEATHER_API_KEY" ]; then
        ENV_VARS="$ENV_VARS,OPENWEATHER_API_KEY=$OPENWEATHER_API_KEY"
    fi
    
    if [ -n "$ENV_VARS" ]; then
        gcloud run services update $SERVICE_NAME \
            --region $REGION \
            --set-env-vars "${ENV_VARS:1}"  # Remove leading comma
    fi
    
    log_info "Environment variables set!"
}

# ============================================================================
# Cleanup Old Revisions
# ============================================================================
cleanup() {
    log_info "Cleaning up old revisions..."
    
    # Keep only the last 3 revisions
    gcloud run revisions list \
        --service $SERVICE_NAME \
        --region $REGION \
        --format "value(name)" \
        --sort-by "~creationTimestamp" | tail -n +4 | while read revision; do
        log_info "Deleting old revision: $revision"
        gcloud run revisions delete $revision --region $REGION --quiet || true
    done
    
    log_info "Cleanup complete!"
}

# ============================================================================
# Display Usage
# ============================================================================
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  deploy    - Full deployment (build, push, deploy)"
    echo "  build     - Build Docker image only"
    echo "  push      - Push image to GCR"
    echo "  update    - Update Cloud Run service"
    echo "  cleanup   - Clean up old revisions"
    echo "  logs      - View service logs"
    echo "  status    - Check service status"
    echo ""
    echo "Environment Variables:"
    echo "  GCP_PROJECT_ID  - Google Cloud project ID (required)"
    echo "  GCP_REGION      - Deployment region (default: us-central1)"
    echo ""
}

# ============================================================================
# View Logs
# ============================================================================
view_logs() {
    log_info "Viewing Cloud Run logs..."
    
    gcloud run services logs read $SERVICE_NAME \
        --region $REGION \
        --limit 100
}

# ============================================================================
# Check Status
# ============================================================================
check_status() {
    log_info "Checking service status..."
    
    gcloud run services describe $SERVICE_NAME \
        --region $REGION \
        --format "yaml(status)"
}

# ============================================================================
# Main Entry Point
# ============================================================================
main() {
    case "${1:-deploy}" in
        deploy)
            preflight_checks
            authenticate
            build_image
            push_image
            deploy
            set_env_vars
            ;;
        build)
            build_image
            ;;
        push)
            authenticate
            push_image
            ;;
        update)
            preflight_checks
            authenticate
            deploy
            ;;
        cleanup)
            authenticate
            cleanup
            ;;
        logs)
            view_logs
            ;;
        status)
            check_status
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main
main "$@"
