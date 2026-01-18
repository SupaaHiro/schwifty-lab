using ApiResilience.Client;
using ApiResilience.Logger;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

var builder = Host.CreateApplicationBuilder(args);

/* Configure application configuration sources */
builder.Configuration.AddJsonFile("appsettings.json", optional: false, reloadOnChange: true);
builder.Configuration.AddEnvironmentVariables();
builder.Configuration.AddCommandLine(args);
builder.Configuration.AddUserSecrets<Program>();

/* Add logging */
builder.Services.AddLogging(builder =>
{
    builder.ClearProviders();
    builder.AddColorConsoleLogger();
});

/* Configure HTTP client with resilience patterns for the WeatherForecastClient */
builder.Services
  .AddHttpClient<WeatherForecastClient>(client =>
  {
      var url = builder.Configuration.GetValue<string>("ServerEndpointUrl") ?? throw new InvalidProgramException("Unable to find ServerEndpointUrl configuration value.");
      client.BaseAddress = new Uri(url);
  })
  .AddStandardResilienceHandler(options =>
{
    var httpClientLogger = builder.Services.BuildServiceProvider().GetRequiredService<ILogger<WeatherForecastClient>>();

    /* Rate Limiter: Limits the number of concurrent requests to prevent overwhelming the server */
    options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;

    /* Total Request Timeout: Sets the maximum time allowed for the entire operation, including all retry attempts. */
    options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(5);

    /* Retry Policy: Automatically retries failed requests with jitter to reduce thundering herd effects.
     *   MaxRetryAttempts: Maximum number of retry attempts
     *   Delay: Base delay with jitter (randomization) applied
     *   UseJitter: Adds randomness to retry delays to prevent synchronized retries
     */
    options.Retry.MaxRetryAttempts = 5;
    options.Retry.OnRetry = args =>
    {
        httpClientLogger.LogTrace("  Retrying request. Attempt {attempt}.", args.AttemptNumber + 1);

        return default;
    };
    options.Retry.Delay = TimeSpan.FromMilliseconds(20);
    options.Retry.UseJitter = true;

    /* Circuit Breaker: Monitors request failures and opens the circuit to prevent cascading failures.
     *   SamplingDuration: Evaluates failure rate over a X-second window
     *   FailureRatio: Opens circuit when X% of requests fail
     *   MinimumThroughput: Requires at least X requests before evaluating failure ratio
     *   BreakDuration: Keeps circuit open for X seconds before attempting recovery (half-open state)
     *   Event handlers log state transitions: CLOSED (normal), OPENED (failing), HALF-OPEN (testing recovery)
     */
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

    /* Attempt Timeout: Sets the maximum time allowed for each individual request attempt */
    options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(100);
});

/* Add the Worker as a hosted service */
builder.Services.AddHostedService<Worker>();

var app = builder.Build();
await app.RunAsync();
