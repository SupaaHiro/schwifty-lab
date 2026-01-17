using ApiResilience.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Http.Resilience;

static void ConfigureLogger(ILoggingBuilder builder)
{
  builder.ClearProviders();
  builder.AddColorConsoleLogger();
}

var builder = Host.CreateApplicationBuilder(args);

// Configure application configuration sources
builder.Configuration.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
builder.Configuration.AddEnvironmentVariables();
builder.Configuration.AddCommandLine(args);
builder.Configuration.AddUserSecrets<Program>();

builder.Services.AddLogging(ConfigureLogger);
builder.Services
  .AddHttpClient<WeatherForecastClient>(client => {
    var url = builder.Configuration.GetValue<string>("ServerEndpointUrl") ?? throw new InvalidProgramException("Unable to find ServerEndpointUrl configuration value.");
    client.BaseAddress = new Uri(url);
  })
  .AddStandardResilienceHandler(options =>
{
  var httpClientLogger = builder.Services.BuildServiceProvider().GetRequiredService<ILogger<WeatherForecastClient>>();
  
  options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;

  options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(5);

  options.Retry.MaxRetryAttempts = 5;
  options.Retry.OnRetry = args =>
  {
    httpClientLogger.LogWarning("  Retrying request. Attempt {attempt}.", args.AttemptNumber + 1);

    return default;
  };
  options.Retry.Delay = TimeSpan.FromMilliseconds(20);
  options.Retry.UseJitter = true;

  options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(5);
  options.CircuitBreaker.FailureRatio = 0.9;
  options.CircuitBreaker.MinimumThroughput = 5;
  options.CircuitBreaker.BreakDuration = TimeSpan.FromSeconds(10);
  options.CircuitBreaker.OnClosed = args =>
  {
    httpClientLogger.LogWarning("  CircuitBreaker CLOSED");
    return default;
  };
  options.CircuitBreaker.OnOpened = args =>
  {
    httpClientLogger.LogWarning("  CircuitBreaker OPENED");
    return default;
  };
  options.CircuitBreaker.OnHalfOpened = args =>
  {
    httpClientLogger.LogWarning("  CircuitBreaker HALF-OPEN");
    return default;
  };

  options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(100);
});
builder.Services.AddHostedService<Worker>();

var app = builder.Build();
await app.RunAsync();
