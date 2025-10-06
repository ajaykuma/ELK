#!/bin/bash

set -e
cd /home/hdu

start_time=$(date +%s)

echo "cleaning old data"

rm -rf cluster-configs/Node1/data cluster-configs/Node1/logs/* \
rm -rf cluster-configs/Node2/data cluster-configs/Node2/logs/* \
rm -rf cluster-configs/Node2/data cluster-configs/Node2/logs/* 

ES_PATH_CONF=cluster-configs/Node1 elasticsearch > node1_nsec.log 2>&1 &

until curl -s http://localhost:9200 >/dev/null 2>&1; do
  sleep 5
  echo "   still waiting..."
done
echo "Elasticsearch is up!"

echo "Starting second node"
ES_PATH_CONF=cluster-configs/Node2 elasticsearch > node2_nsec.log 2>&1 &

until curl -s http://localhost:9201 >/dev/null 2>&1; do
  sleep 5
  echo "   still waiting..."
done
echo "Elasticsearch is up on 2nd node!"

echo "Starting third node"
ES_PATH_CONF=cluster-configs/Node3 elasticsearch > node3_nsec.log 2>&1 &

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
echo "   - node1_nsec.log"
echo "   - node2_nsec.log"
echo "   - node3_nsec.log"

echo "http://localhost:9200/_cat/nodes?v"

curl http://localhost:9200/_cat/nodes?v
echo "http://localhost:9201/_cat/nodes?v"
curl http://localhost:9201/_cat/nodes?v
echo "http://localhost:9202/_cat/nodes?v"
curl http://localhost:9202/_cat/nodes?v

echo "to kill all nodes: pkill -f elasticsearch"
