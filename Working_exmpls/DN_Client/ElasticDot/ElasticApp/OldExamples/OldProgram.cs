using Nest;
using System;

public class Product
{
    public int Id { get; set; }
    public string? Name { get; set; }
    public double Price { get; set; }
}


class OldProgram
{
    public static void Test()
    {
        var settings = new ConnectionSettings(new Uri("http://localhost:9200"))
            .DefaultIndex("products");

        var client = new ElasticClient(settings);

        // Test connection
        var ping = client.Ping();
        Console.WriteLine(ping.IsValid
            ? "Connected to Elasticsearch!"
            : $"Connection failed: {ping.OriginalException?.Message}");

        // Index sample data
        var product = new Product { Id = 1, Name = "Laptop", Price = 1299.99 };
        var indexResponse = client.IndexDocument(product);
        Console.WriteLine(indexResponse.IsValid
            ? " Document indexed successfully!"
            : $"Index failed: {indexResponse.DebugInformation}");

        // Search
        var searchResponse = client.Search<Product>(s => s
            .Query(q => q
                .Match(m => m
                    .Field(f => f.Name)
                    .Query("Laptop")
                )
            )
        );

        Console.WriteLine("Search results:");
        foreach (var hit in searchResponse.Hits)
            Console.WriteLine($"- {hit.Source.Name} (${hit.Source.Price})");
    }
}

