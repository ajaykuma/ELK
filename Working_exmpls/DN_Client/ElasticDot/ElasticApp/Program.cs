using System;
using ElasticApp.Models;
using ElasticApp.Services;

class Program
{
    static void Main()
    {
        var client = ElasticsearchClientFactory.CreateClient();
        var productService = new ProductService(client);
        var indexService = new IndexService(client);

        while (true)
        {
            Console.WriteLine("\n=== Elasticsearch Menu ===");
            Console.WriteLine("1 - List Nodes");
            Console.WriteLine("2 - List Indices");
            Console.WriteLine("3 - Create Index");
            Console.WriteLine("4 - Delete Index");
            Console.WriteLine("5 - Index Product");
            Console.WriteLine("6 - Search Product");
            Console.WriteLine("0 - Exit");
            Console.Write("Choose: ");
            var choice = Console.ReadLine();

            switch (choice)
            {
                case "1":
                    indexService.ListNodes();
                    break;
                case "2":
                    indexService.ListIndices();
                    break;
                case "3":
                    Console.Write("Enter index name: ");
                    indexService.CreateIndex(Console.ReadLine() ?? "default");
                    break;
                case "4":
                    Console.Write("Enter index name: ");
                    indexService.DeleteIndex(Console.ReadLine() ?? "default");
                    break;
                case "5":
                    var product = new Product();
                    Console.Write("Product Id: "); product.Id = int.Parse(Console.ReadLine() ?? "0");
                    Console.Write("Name: "); product.Name = Console.ReadLine() ?? "";
                    Console.Write("Price: "); product.Price = double.Parse(Console.ReadLine() ?? "0");
                    productService.IndexProduct(product);
                    break;
                case "6":
                    Console.Write("Search keyword: ");
                    productService.SearchProduct(Console.ReadLine() ?? "");
                    break;
                case "0":
                    return;
                default:
                    Console.WriteLine("Invalid choice.");
                    break;
            }
        }
    }
}

