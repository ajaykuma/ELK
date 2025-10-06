#!/bin/bash

set -e
cd /home/hdu

start_time=$(date +%s)

echo "cleaning old data"

rm -rf elasticsearch/data/* elasticsearch/logs/* \
rm -rf cluster-configs-2/data/* cluster-configs-2/logs/* \
rm -rf cluster-configs-3/data/* cluster-configs-3/logs
elasticsearch > elasticsearch_login_nsec.log 2>&1 &

until curl -s http://localhost:9200 >/dev/null 2>&1; do
  sleep 5
  echo "   still waiting..."
done
echo "Elasticsearch is up!"

echo "Starting second node"
ES_PATH_CONF=cluster-configs-2 elasticsearch > node2.log 2>&1 &

until curl -s http://localhost:9201 >/dev/null 2>&1; do
  sleep 5
  echo "   still waiting..."
done
echo "Elasticsearch is up on 2nd node!"

echo "Starting third node"
ES_PATH_CONF=cluster-configs-3 elasticsearch > node3.log 2>&1 &

until curl -s http://localhost:9202 >/dev/null 2>&1; do
  sleep 5
  echo "   still waiting..."
done
echo "Elasticsearch is up on 3rd node!"

end_time=$(date +%s)
duration=$((end_time - start_time))

echo "All nodes started successfully!"
echo "Total startup time: ${duration} seconds"

echo "Logs:"
echo "   - elasticsearch_login.log"
echo "   - node2.log"
echo "   - node3.log"

echo "http://localhost:9200/_cat/nodes?v"
curl http://localhost:9200/_cat/nodes?v
echo "http://localhost:9201/_cat/nodes?v"
curl http://localhost:9201/_cat/nodes?v
echo "http://localhost:9202/_cat/nodes?v"
curl http://localhost:9202/_cat/nodes?v

echo "to kill all nodes: pkill -f elasticsearch"