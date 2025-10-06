#!/bin/bash
set -e  # Exit on first error
cd /home/hdu

start_time=$(date +%s)


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