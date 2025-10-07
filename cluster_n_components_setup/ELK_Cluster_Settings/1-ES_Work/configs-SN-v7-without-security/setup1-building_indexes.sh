#!/bin/bash

set -e
cd /home/hdu

start_time=$(date +%s)

echo 'listing nodes'
curl -s http://localhost:9200/_cat/nodes?v

echo 'listing indexes'
curl -s http://localhost:9200/_cat/indices?v

curl -XPUT "http://localhost:9200/ecommerce" -H "Content-Type: application/json" -d '{"settings":{"number_of_shards":3,"number_of_replicas":2,"auto_expand_replicas":false}}'
curl -XPUT "http://localhost:9200/recipes" -H "Content-Type: application/json" -d '{"settings":{"number_of_shards":3,"number_of_replicas":2,"auto_expand_replicas":false}}'
curl -XPUT "http://localhost:9200/customers" -H "Content-Type: application/json" -d '{"settings":{"number_of_shards":3,"number_of_replicas":2,"auto_expand_replicas":false}}'

#The request body must be newline-delimited JSON (NDJSON) 
#— each action line (index) must be followed by its document line

echo 'loading data in ecommerce'
curl -XPOST "http://localhost:9200/ecommerce/_bulk" -H "Content-Type: application/json" --data-binary @datasets/bulk_data.json

echo 'loading data in recipes'
curl -XPOST 'http://localhost:9200/recipes/_bulk' -H "Content-Type: application/json" --data-binary @datasets/recipes2.json

echo 'loading data in customers'curl -XPOST 'http://localhost:9200/recipes/_bulk' -H "Content-Type: application/json" --data-binary @datasets/customers2_compact.json

echo 'counts'
GET ecommerce/_count
GET recipes/_count
GET customers/_count

