#to send data to Opensearch change the output section as follows (as done in logstash_bankcsv.conf,fb_pipline.conf)

output {
  opensearch {
    hosts => ["http://a1:9200","http://a2:9200","http://a3:9200"]
    index => "bankdata"
  }

OR

output {
    opensearch {
        hosts       => ["hostname:port"]
        user        => "admin"
        password    => "admin"
        index       => "logstash-data-%{+YYYY.MM.dd}"
    }
}

OR
In addition to the existing authentication mechanisms, if we want to add new authentication then we will be adding them in the configuration by using auth_type.

Example Configuration for basic authentication:

output {
    opensearch {
          hosts  => ["hostname:port"]
          auth_type => {
              type => 'basic'
              user => 'admin'
              password => 'admin'
          }
          index => "logstash-logs-%{+YYYY.MM.dd}"
   }
}

To ingest data into a data stream through logstash, we need to create the data stream and specify the name of data stream and the op_type of create in the output configuration. The sample configuration is shown below:

output {
    opensearch {
          hosts  => ["https://hostname:port"]
          auth_type => {
              type => 'basic'
              user => 'admin'
              password => 'admin'
          }
          index => "my-data-stream"
          action => "create"
   }
}

