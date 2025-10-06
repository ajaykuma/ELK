#!/bin/bash
set -e  # Exit on first error
cd /home/hdu

start_time=$(date +%s)

# ---------------------------------------------------------------------
# CONFIGURATION PATHS
# ---------------------------------------------------------------------
CONFIGS=(
  "elasticsearch/config/elasticsearch.yml"
  "cluster-configs-2/elasticsearch.yml"
  "cluster-configs-3/elasticsearch.yml"
)

# ---------------------------------------------------------------------
# CLEANUP STEP
# ---------------------------------------------------------------------
echo "Cleaning up old data, logs, certs, and keystores..."
for path in elasticsearch cluster-configs-2 cluster-configs-3; do
  rm -rf "$path/data"/* || true
  rm -rf "$path/logs"/* || true
  rm -rf "$path/config/certs" || true
  rm -f  "$path/config/elasticsearch.keystore" || true
done

# ---------------------------------------------------------------------
# CONFIG UPDATE STEP
# ---------------------------------------------------------------------
echo "Clean up configs to remove any x-pack security settings, comment out discovery/master settings..."
echo "come back again once done and rerun this script"

echo "Configs cleaned. Elasticsearch will self-bootstrap security settings."

# ---------------------------------------------------------------------
# STARTUP STEP
# ---------------------------------------------------------------------
echo "Starting main Elasticsearch node (node1)..."
elasticsearch > elasticsearch_login_wsec.log 2>&1 &

# Wait for Elasticsearch to fully start and configure security
echo "Waiting for node1 (main) to finish security setup..."
timeout=180
elapsed=0

while ! grep -q "Elasticsearch security features have been automatically configured!" elasticsearch_login_wsec.log; do
  sleep 3
  elapsed=$((elapsed + 3))
  if [ "$elapsed" -ge "$timeout" ]; then
    echo "Timeout: node1 did not complete security setup within ${timeout}s."
    echo "Check elasticsearch_login_wsec.log for details."
    exit 1
  fi
done

echo "Elasticsearch security features have been automatically configured!"
grep -A10 "Elasticsearch security features have been automatically configured!" elasticsearch_login_wsec.log | tee important_info.log

# Capture and print key info from logs
grep -E 'Password|fingerprint|token' elasticsearch_login_wsec.log || true

# ---------------------------------------------------------------------
# TOKEN GENERATION AND NODE STARTUP
# ---------------------------------------------------------------------
echo "Generating enrollment token for other nodes..."
token=$(elasticsearch-create-enrollment-token -s node)
echo "Enrollment token generated: $token" | tee enrollment_token.txt

echo "Starting node2..."
ES_PATH_CONF=cluster-configs-2 elasticsearch --enrollment-token "$token" > node2.log 2>&1 &

echo "Starting node3..."
ES_PATH_CONF=cluster-configs-3 elasticsearch --enrollment-token "$token" > node3.log 2>&1 &

# Wait a little for nodes to initialize
sleep 15

end_time=$(date +%s)
duration=$((end_time - start_time))

# ---------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------
echo "All nodes started successfully!"
echo "Total startup time: ${duration} seconds"
echo "Logs:"
echo "   - elasticsearch_login_wsec.log"
echo "   - node2.log"
echo "   - node3.log"
echo "Enrollment token saved to enrollment_token.txt"