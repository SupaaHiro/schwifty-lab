using ApiResilience.Client;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

static void ConfigureLogger(ILoggingBuilder builder)
{
  builder.ClearProviders();
  builder.AddColorConsoleLogger((config) => config.SimplifiedOutput = true);
}

var builder = Host.CreateApplicationBuilder(args);

// Configure application configuration sources
builder.Configuration.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
builder.Configuration.AddEnvironmentVariables();
builder.Configuration.AddCommandLine(args);
builder.Configuration.AddUserSecrets<Program>();

var url = builder.Configuration.GetValue<string>("ServerEndpointUrl") ?? throw new InvalidProgramException("Unable to find ServerEndpointUrl configuration value.");
builder.Services.AddLogging(ConfigureLogger);
builder.Services.AddHttpClient<WeatherForecastClient>(client =>
{
  client.BaseAddress = new Uri(url);
}).AddStandardResilienceHandler((options) =>
{
  var httpClientLogger = LoggerFactory.Create(ConfigureLogger).CreateLogger<WeatherForecastClient>();

  options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;

  options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(2);

  options.Retry.MaxRetryAttempts = 2;
  options.Retry.OnRetry = args =>
  {
    if (args.AttemptNumber > 0)
      httpClientLogger.LogWarning("  Retrying request. Attempt {attempt}.", args.AttemptNumber);

    return default;
  };
  options.Retry.Delay = TimeSpan.FromMilliseconds(100);

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

  options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(500);
});
builder.Services.AddHostedService<Worker>();

var app = builder.Build();
await app.RunAsync();
