using Nest;
using System;

namespace ElasticApp.Services
{
    public static class ElasticsearchClientFactory
    {
        private static readonly Uri node = new Uri("http://localhost:9200");

        public static ElasticClient CreateClient()
        {
            var settings = new ConnectionSettings(node)
                .DefaultIndex("products");
            return new ElasticClient(settings);
        }
    }
}

