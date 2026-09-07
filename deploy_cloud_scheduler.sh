#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Scheduler Deployment Script
# Personal Search Assistant - Automated Daily Evening Execution
# ==============================================================================

set -euo pipefail

USER_ID="${1:-noam}"
SERVICE_URL="${2:-}"
TIMEZONE="${3:-Asia/Jerusalem}"
JOB_NAME="evening-search-assistant-${USER_ID}"
CRON_SCHEDULE="0 20 * * *" # Every day at 20:00 (8:00 PM)

if [ -z "${SERVICE_URL}" ]; then
  echo "Error: Cloud Run Service URL is required."
  echo "Usage: ./deploy_cloud_scheduler.sh <USER_ID> <SERVICE_URL> [TIMEZONE]"
  echo "Example: ./deploy_cloud_scheduler.sh noam https://personal-search-assistant-xyz-uc.a.run.app"
  exit 1
fi

TARGET_URI="${SERVICE_URL}/api/tasks/run-all?user_id=${USER_ID}"

echo "======================================================================"
echo " Deploying Google Cloud Scheduler Job"
echo " Job Name  : ${JOB_NAME}"
echo " Schedule  : ${CRON_SCHEDULE} (${TIMEZONE})"
echo " Target URI: ${TARGET_URI}"
echo "======================================================================"

# Check if job already exists
if gcloud scheduler jobs describe "${JOB_NAME}" --location="us-central1" &>/dev/null; then
  echo "Updating existing Cloud Scheduler job '${JOB_NAME}'..."
  gcloud scheduler jobs update http "${JOB_NAME}" \
    --location="us-central1" \
    --schedule="${CRON_SCHEDULE}" \
    --time-zone="${TIMEZONE}" \
    --uri="${TARGET_URI}" \
    --http-method=POST \
    --description="Daily evening task execution for user '${USER_ID}'"
else
  echo "Creating new Cloud Scheduler job '${JOB_NAME}'..."
  gcloud scheduler jobs create http "${JOB_NAME}" \
    --location="us-central1" \
    --schedule="${CRON_SCHEDULE}" \
    --time-zone="${TIMEZONE}" \
    --uri="${TARGET_URI}" \
    --http-method=POST \
    --description="Daily evening task execution for user '${USER_ID}'"
fi

echo ""
echo "✓ Cloud Scheduler job '${JOB_NAME}' successfully deployed!"
echo "To test execution manually:"
echo "  gcloud scheduler jobs run ${JOB_NAME} --location=us-central1"
