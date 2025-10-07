#!/bin/bash
sudo apt install -y npm
sudo npm install -g csvtojson
csvtojson Bank_full.csv > bankdata.json
#Elasticsearch bulk API needs action line + document line
sudo apt install -y jq
jq -c '.[] | {"index":{"_index":"bankdata"}} , .' bankdata.json > bankdata_bulk.json
curl -s -H "Content-Type: application/json" -XPOST 'http://localhost:9200/_bulk' --data-binary @bankdata_bulk.json
curl -XGET "http://localhost:9200/bankdata/_count" \
     -H "Content-Type: application/json" \
     -d '{
       "query": {
         "match_all": {}
       }
     }'
