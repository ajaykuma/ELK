using Nest;
using System;

namespace ElasticApp.Services
{
    public class IndexService
    {
        private readonly ElasticClient _client;

        public IndexService(ElasticClient client)
        {
            _client = client;
        }

        public void ListIndices()
        {
            var response = _client.Cat.Indices();
            Console.WriteLine("=== Indices ===");
            foreach (var idx in response.Records)
                Console.WriteLine($"{idx.Index} | Docs: {idx.DocsCount} | Size: {idx.StoreSize}");
        }

        public void CreateIndex(string indexName)
        {
            var response = _client.Indices.Create(indexName, c => c);
            Console.WriteLine(response.IsValid ? $"Index '{indexName}' created." : $"Failed to create {indexName}");
        }

        public void DeleteIndex(string indexName)
        {
            var response = _client.Indices.Delete(indexName);
            Console.WriteLine(response.IsValid ? $"Index '{indexName}' deleted." : $" Failed to delete {indexName}");
        }

        public void ListNodes()
        {
            var nodes = _client.Cat.Nodes();
            Console.WriteLine("=== Cluster Nodes ===");
            foreach (var node in nodes.Records)
                Console.WriteLine($"{node.Name} ({node.Ip}) Heap: {node.HeapPercent}%");
        }
    }
}

