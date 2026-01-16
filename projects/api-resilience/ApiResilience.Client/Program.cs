using ApiResilience.Client;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
var logger = loggerFactory.CreateLogger("ApiResilience.Client");
var builder = Host.CreateApplicationBuilder(args);

builder.Services.AddHttpClient<WeatherForecastClient>(client =>
{
  client.BaseAddress = new Uri("https://localhost:3000");
}).AddStandardResilienceHandler(options =>
{
  options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;

  options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(2);
  
  options.Retry.MaxRetryAttempts = 2;
  options.Retry.OnRetry = args =>
  {
    logger.LogWarning("  Retrying request. Attempt {attempt}.", args.AttemptNumber);

    return default;
  };
  options.Retry.Delay = TimeSpan.FromMilliseconds(100);

  options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(5);
  options.CircuitBreaker.FailureRatio = 0.9;
  options.CircuitBreaker.MinimumThroughput = 5;
  options.CircuitBreaker.BreakDuration = TimeSpan.FromSeconds(10);
  options.CircuitBreaker.OnClosed = args =>
  {
    logger.LogWarning("  CircuitBreaker CLOSED");
    return default;
  };
  options.CircuitBreaker.OnOpened = args =>
  {
    logger.LogError("  CircuitBreaker OPENED");
    return default;
  };
  options.CircuitBreaker.OnHalfOpened = args =>
  {
    logger.LogWarning("  CircuitBreaker HALF-OPEN");
    return default;
  };

  options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(500);
});
builder.Services.AddHostedService<Worker>();

var app = builder.Build();
await app.RunAsync();
