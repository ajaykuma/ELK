using Nest;
using ElasticApp.Models;
using System;

namespace ElasticApp.Services
{
    public class ProductService
    {
        private readonly ElasticClient _client;

        public ProductService(ElasticClient client)
        {
            _client = client;
        }

        public void IndexProduct(Product product)
        {
            var response = _client.IndexDocument(product);
            Console.WriteLine(response.IsValid ? "Product indexed!" : " Failed to index.");
        }

        public void SearchProduct(string keyword)
        {
            var searchResponse = _client.Search<Product>(s => s
                .Query(q => q
                    .Match(m => m
                        .Field(f => f.Name)
                        .Query(keyword)
                    )
                )
            );

            Console.WriteLine("Search results:");
            foreach (var hit in searchResponse.Hits)
                Console.WriteLine($"- {hit.Source.Name} (${hit.Source.Price})");
        }
    }
}

