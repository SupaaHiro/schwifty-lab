using ApiResilience.Contracts;
using ApiResilience.Logger;
using ApiResilience.Server;
using Microsoft.AspNetCore.Http.Features;
using Scalar.AspNetCore;

var builder = WebApplication.CreateBuilder(args);

// Configure application configuration sources
builder.Configuration.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
builder.Configuration.AddEnvironmentVariables();
builder.Configuration.AddCommandLine(args);
builder.Configuration.AddUserSecrets<Program>();

// Add logging
builder.Services.AddLogging(builder =>
{
    builder.ClearProviders();
    builder.AddColorConsoleLogger();
});

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// Add error handling middleware with custom problem details
builder.Services.AddProblemDetails(options =>
{
    options.CustomizeProblemDetails = context =>
    {
        // Sets the instance to the HTTP method and path of the request.
        context.ProblemDetails.Instance = $"{context.HttpContext.Request.Method} {context.HttpContext.Request.Path}";

        // Adds the request ID to the problem details extensions.
        context.ProblemDetails.Extensions.TryAdd("messageId", context.HttpContext.TraceIdentifier);

        // Adds the trace ID from the activity feature to the problem details extensions.
        var activity = context.HttpContext.Features.Get<IHttpActivityFeature>()?.Activity;
        context.ProblemDetails.Extensions.TryAdd("traceId", activity);
    };
});
builder.Services.AddExceptionHandler<GlobalExceptionHandler>();

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
    app.MapScalarApiReference();
}

app.UseMiddleware<RequestTimingMiddleware>();
app.UseExceptionHandler();
app.UseHttpsRedirection();

var summaries = new[] { "Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching" };

app.MapGet("/weatherforecast", async () =>
{
    // Simulate random delays and errors to test the resilience pipeline of the client
    var chance = Random.Shared.NextDouble();
    if (chance < 0.2)
        await Task.Delay(5_000);
    else if (chance < 0.4)
        throw new ResponseInternalErrorException("Something went wrong while fetching the weather forecast.");

    // Happy path: return a 5-day weather forecast
    var forecast = Enumerable.Range(1, 5).Select(index =>
          new WeatherForecast
          (
              DateOnly.FromDateTime(DateTime.UtcNow.AddDays(index)),
              Random.Shared.Next(-20, 55),
              summaries[Random.Shared.Next(summaries.Length)]
          ))
          .ToArray();
    return forecast;
})
.WithName("GetWeatherForecast");

app.Run();