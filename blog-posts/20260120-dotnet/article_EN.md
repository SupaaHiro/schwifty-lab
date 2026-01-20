---
layout: default
title: "Building Resilient Applications with .NET Resilience Pipelines"
date: 2026-01-20
categories: [dotnet, resilience, http]
author: Hiro
image: "https://supaahiro.github.io/schwifty-lab/blog-posts/20260120-dotnet/article.webp"
summary: "Learn how to build resilient HTTP clients in .NET using the standard resilience handler. Discover retry policies, circuit breakers, timeouts, and rate limiting through a hands-on demo application."
---

## Introduction

I recently stumbled upon a [video](https://www.youtube.com/watch?v=pgeHRp2Otlc) that explains resilience pipelines in .NET. Unfortunately, the source code was only available for Patreon supporters, and since I was already evaluating Visual Studio 2026, I thought: why not create a project to demonstrate how they work? I started with a simple ASP.NET Core Web API, but then one thing led to another, and I ended up with a project that I thought was worth sharing and documenting.

In modern distributed systems, network failures, service degradations, and transient errors are inevitable. Building resilient applications that can gracefully handle these failures is crucial for delivering a reliable user experience. In this article, we'll explore how to leverage .NET's **resilience pipelines** to create robust HTTP clients that can withstand various failure scenarios.

This article introduce a complete demo application consisting of a server that simulates realistic failure scenarios (random delays and errors) and a client that demonstrates how resilience patterns automatically handle these issues. By the end of this article, you'll understand how to configure retry policies, circuit breakers, timeouts, and rate limiting to build production-ready resilient applications.

## Prerequisites

- .NET 10 SDK or later
- Basic understanding of HTTP clients in .NET
- Familiarity with dependency injection and hosted services

## Getting the Resources

Clone the lab repository and navigate to this article's folder:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/projects/api-resilience
```

The solution contains four projects:

- **ApiResilience.Contracts**: Shared data contracts
- **ApiResilience.Logger**: Custom colored console logger
- **ApiResilience.Server**: ASP.NET Core Web API with Blazor UI
- **ApiResilience.Client**: Background worker that calls the API

## Understanding the Problem: Transient Failures

Before diving into resilience patterns, let's understand what problems we're trying to solve. Distributed systems commonly face:

- **Transient network errors**: Temporary connection issues that resolve quickly
- **Service degradation**: Slow responses due to high load or resource constraints
- **Service failures**: Complete unavailability of downstream services
- **Rate limiting**: Service throttling to protect resources

Without proper resilience strategies, these issues can cascade through your application, leading to poor user experience or complete system failures.

## The Demo Application Architecture

Our demo application simulates real-world failure scenarios in a controlled environment:

### The Server: Configurable Failure Injection

The server exposes a simple weather forecast API endpoint (`/weatherforecast`) but with a twist: it can randomly inject delays and errors based on configurable probabilities. This allows us to test how resilience patterns handle various failure rates.

#### Server Configuration

The server's behavior is controlled through `appsettings.json`:

```json
{
  "Server": {
    "WarmupSeconds": 10,
    "DelayProbability": 0.2,
    "DelayDurationMs": 5000,
    "ErrorProbability": 0.2
  }
}
```

Let's break down these settings:

- **WarmupSeconds**: Grace period after startup before injecting failures (useful for initial testing)
- **DelayProbability**: Percentage of requests that will have a delay (0.2 = 20%)
- **DelayDurationMs**: Duration of the delay when triggered (in milliseconds)
- **ErrorProbability**: Percentage of requests that will throw an error (0.2 = 20%)

The implementation randomly decides whether to delay or fail a request:

```csharp
var serverSettings = settingsService.GetRuntimeSettings();

var elapsedSeconds = (DateTimeOffset.UtcNow - appStartTime).TotalSeconds;
if (elapsedSeconds >= serverSettings.WarmupSeconds)
{
    var chance = Random.Shared.NextDouble();
    if (chance < serverSettings.ErrorProbability)
        throw new ResponseInternalErrorException("Something went wrong...");
    else if (chance < serverSettings.ErrorProbability + serverSettings.DelayProbability)
        await Task.Delay(serverSettings.DelayDurationMs);
}

// Return weather forecast data
var forecast = Enumerable.Range(1, 5).Select(index =>
    new WeatherForecast(
        DateOnly.FromDateTime(DateTime.UtcNow.AddDays(index)),
        Random.Shared.Next(-20, 55),
        summaries[Random.Shared.Next(summaries.Length)]
    ))
    .ToArray();
return forecast;
```

#### Global Exception Handler

The server uses a global exception handler to catch and properly format all errors:

```csharp
public sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var problemDetails = new ProblemDetails
        {
            Status = StatusCodes.Status500InternalServerError,
            Title = "Internal Server Error",
            Detail = exception.Message,
            Instance = $"{httpContext.Request.Method} {httpContext.Request.Path}"
        };

        httpContext.Response.StatusCode = (int)problemDetails.Status;
        await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

        logger.LogTrace("  Handled {Exception} for request {Method} {Path}",
            exception.GetType().Name, httpContext.Request.Method, httpContext.Request.Path);

        return true;
    }
}
```

This ensures all exceptions are consistently logged and returned as proper HTTP 500 responses with structured problem details.

#### Blazor Settings Page

The server includes a Blazor page at `/settings` that allows you to dynamically adjust failure rates without restarting the application:

```csharp
@page "/settings"
@inject ServerSettingsService SettingsService

<EditForm Model="@editModel" OnValidSubmit="@HandleValidSubmit">
  <div class="form-group">
    <label for="delayProbability">Delay Probability:</label>
    <InputNumber id="delayProbability" @bind-Value="editModel.DelayProbability" step="0.01" />
    <small>Probability of introducing delay (0.0-1.0 where 0.2 = 20%)</small>
  </div>

  <div class="form-group">
    <label for="errorProbability">Error Probability:</label>
    <InputNumber id="errorProbability" @bind-Value="editModel.ErrorProbability" step="0.01" />
    <small>Probability of throwing errors (0.0-1.0 where 0.2 = 20%)</small>
  </div>

  <button type="submit" class="btn btn-primary">Apply Settings</button>
</EditForm>
```

This interactive interface makes it easy to experiment with different failure scenarios in real-time.

### The Client: Resilient HTTP Worker

The client is a background worker that continuously calls the weather forecast API every second. It uses .NET's standard resilience handler to automatically handle failures.

#### Worker Implementation

```csharp
public sealed class Worker(ILogger<Worker> logger, WeatherForecastClient client)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            await ExecuteOneAsync(stoppingToken);
            await Task.Delay(1_000, stoppingToken);
        }
    }

    private async Task ExecuteOneAsync(CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        try
        {
            _ = await client.GetWeatherForecastAsync(cancellationToken);
            stopwatch.Stop();

            var duration = stopwatch.ElapsedMilliseconds;
            if (duration >= 1_000)
                logger.LogWarning("200 (OK): {duration}ms", duration);
            else
                logger.LogInformation("200 (OK): {duration}ms", duration);
        }
        catch (HttpRequestException httpEx)
        {
            stopwatch.Stop();
            logger.LogError("Err ({statusCode}): {duration}ms",
                (int?)httpEx.StatusCode ?? 0, stopwatch.ElapsedMilliseconds);
        }
        catch (TimeoutRejectedException)
        {
            logger.LogError("Err (TimeoutRejectedException): {duration}ms",
                stopwatch.ElapsedMilliseconds);
        }
        catch (BrokenCircuitException)
        {
            logger.LogError("Err (BrokenCircuitException): {duration}ms",
                stopwatch.ElapsedMilliseconds);
        }
    }
}
```

The worker logs each request's outcome with color-coded severity levels (green for success, yellow for warnings, red for errors) thanks to our custom logger.

### Custom Color Console Logger

Both server and client use a custom logger that provides visual feedback through colored console output:

```csharp
public sealed class ColorConsoleLoggerConfiguration
{
    public Dictionary<LogLevel, ConsoleColor> LogLevelToColorMap { get; set; } = new()
    {
        [LogLevel.Information] = ConsoleColor.Green,
        [LogLevel.Warning] = ConsoleColor.Yellow,
        [LogLevel.Error] = ConsoleColor.Red,
        [LogLevel.Critical] = ConsoleColor.DarkRed,
    };

    public bool SimplifiedOutput { get; set; }
}
```

This makes it easy to visually monitor the application's health:
- **Green**: Successful requests
- **Yellow**: Delayed requests or warnings
- **Red**: Errors and failures

## Configuring the Standard Resilience Handler

The magic happens in the client's HTTP client configuration. .NET's `Microsoft.Extensions.Http.Resilience` package provides the `AddStandardResilienceHandler` extension method, which sets up a complete resilience pipeline:

```csharp
builder.Services
    .AddHttpClient<WeatherForecastClient>(client =>
    {
        var url = builder.Configuration.GetValue<string>("ServerEndpointUrl")
            ?? throw new InvalidProgramException("Unable to find ServerEndpointUrl");
        client.BaseAddress = new Uri(url);
    })
    .AddStandardResilienceHandler(options =>
    {
        var httpClientLogger = builder.Services.BuildServiceProvider()
            .GetRequiredService<ILogger<WeatherForecastClient>>();

        // Rate Limiter Configuration
        options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;

        // Total Request Timeout
        options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(5);

        // Retry Policy
        options.Retry.MaxRetryAttempts = 5;
        options.Retry.Delay = TimeSpan.FromMilliseconds(20);
        options.Retry.UseJitter = true;
        options.Retry.OnRetry = args =>
        {
            httpClientLogger.LogTrace("  Retrying request. Attempt {attempt}.",
                args.AttemptNumber + 1);
            return default;
        };

        // Circuit Breaker
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

        // Attempt Timeout
        options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(100);
    });
```

Let's break down each component of the resilience pipeline:

### 1. Rate Limiter

```csharp
options.RateLimiter.DefaultRateLimiterOptions.PermitLimit = 3;
```

The rate limiter prevents overwhelming the server by limiting concurrent requests. With a permit limit of 3, only 3 requests can be in flight simultaneously. Additional requests will be queued or rejected based on the configuration.

### 2. Total Request Timeout

```csharp
options.TotalRequestTimeout.Timeout = TimeSpan.FromSeconds(5);
```

This sets the maximum time for the entire operation, including all retry attempts. If the operation takes longer than 5 seconds (including retries), it will be cancelled. This prevents operations from hanging indefinitely.

### 3. Retry Policy

```csharp
options.Retry.MaxRetryAttempts = 5;
options.Retry.Delay = TimeSpan.FromMilliseconds(20);
options.Retry.UseJitter = true;
```

The retry policy automatically retries failed requests up to 5 times:

- **MaxRetryAttempts**: Number of retry attempts after the initial request
- **Delay**: Base delay between retries (20ms in this case)
- **UseJitter**: Adds randomization to delays to prevent the "thundering herd" problem

With jitter enabled, if multiple clients experience failures simultaneously, they won't all retry at the exact same time, which would overload the recovering service.

The retry logic uses exponential backoff with jitter, so the delays increase progressively:
- Attempt 1: ~20ms
- Attempt 2: ~40ms
- Attempt 3: ~80ms
- And so on...

### 4. Circuit Breaker

The circuit breaker is one of the most important resilience patterns. It prevents cascading failures by "opening" the circuit when too many requests fail, giving the failing service time to recover:

```csharp
options.CircuitBreaker.SamplingDuration = TimeSpan.FromSeconds(5);
options.CircuitBreaker.FailureRatio = 0.9;
options.CircuitBreaker.MinimumThroughput = 5;
options.CircuitBreaker.BreakDuration = TimeSpan.FromSeconds(10);
```

Here's how it works:

- **SamplingDuration**: Evaluates failures over a 5-second rolling window
- **FailureRatio**: Opens the circuit if 90% of requests fail
- **MinimumThroughput**: Requires at least 5 requests before evaluating the failure ratio
- **BreakDuration**: Keeps the circuit open for 10 seconds before attempting recovery

#### Circuit Breaker States

The circuit breaker operates in three states:

1. **CLOSED** (Normal operation): All requests pass through normally
2. **OPENED** (Failing): Circuit is open, requests fail immediately without hitting the server
3. **HALF-OPEN** (Testing recovery): After the break duration, allows a few test requests through

The state transitions are logged to help you understand the circuit breaker's behavior:

```csharp
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
```

### 5. Attempt Timeout

```csharp
options.AttemptTimeout.Timeout = TimeSpan.FromMilliseconds(100);
```

This sets the timeout for each individual request attempt. If a single request takes longer than 100ms, it will be cancelled and potentially retried. This is different from the total request timeout—the attempt timeout applies to each retry, while the total timeout applies to the entire operation.

## Running the Demo: Seeing Resilience in Action

Now let's see how these resilience patterns work in practice. Start both the server and client:

```bash
# Terminal 1 - Start the Server
cd ApiResilience.Server
dotnet run

# Terminal 2 - Start the Client
cd ApiResilience.Client
dotnet run
```

### Scenario 1: Moderate Failures (40% Error + Delay Rate)

With the default configuration (20% delays + 20% errors = 40% total), you'll see:

```
200 (OK): 45ms
200 (OK): 52ms
  Retrying request. Attempt 2.
200 (OK): 78ms
200 (OK): 41ms
  Retrying request. Attempt 2.
  Retrying request. Attempt 3.
200 (OK): 156ms
200 (OK): 39ms
```

**Observations**:
- Most requests succeed immediately (green logs)
- Some requests require retries but eventually succeed
- The client-side application experiences seamless operation
- Users would never know about the underlying failures

### Scenario 2: High Failure Rate (70% Error + Delay Rate)

Navigate to `https://localhost:3000/settings` and adjust the settings:
- Delay Probability: 0.35 (35%)
- Error Probability: 0.35 (35%)

Now you'll start seeing failures even after retries:

```
200 (OK): 43ms
  Retrying request. Attempt 2.
  Retrying request. Attempt 3.
  Retrying request. Attempt 4.
Err (500): 189ms
200 (OK): 47ms
  Retrying request. Attempt 2.
  Retrying request. Attempt 3.
  Retrying request. Attempt 4.
  Retrying request. Attempt 5.
Err (TimeoutRejectedException): 205ms
```

**Observations**:
- More retry attempts are needed
- Some requests fail even after maximum retries
- Timeout exceptions occur when the total request timeout is exceeded
- The application still functions, but with degraded performance

### Scenario 3: Critical Failure Rate (>90% Errors)

Increase the error probability to 0.9 (90%):

```
  Retrying request. Attempt 2.
  Retrying request. Attempt 3.
  Retrying request. Attempt 4.
Err (500): 167ms
  Retrying request. Attempt 2.
  Retrying request. Attempt 3.
Err (500): 98ms
  CircuitBreaker OPENED
Err (BrokenCircuitException): 1ms
Err (BrokenCircuitException): 0ms
Err (BrokenCircuitException): 0ms
  CircuitBreaker HALF-OPEN
  Retrying request. Attempt 2.
200 (OK): 67ms
  CircuitBreaker CLOSED
200 (OK): 44ms
```

**Observations**:
- Multiple requests fail quickly due to high error rate
- Circuit breaker opens after detecting sustained failures
- While open, requests fail immediately (0ms) without hitting the server
- After the break duration, circuit breaker enters half-open state
- Successful test requests cause the circuit to close again

## Understanding the Resilience Pipeline Order

The resilience strategies are applied in a specific order, forming a pipeline:

```
Request Flow:
┌─────────────────┐
│  Rate Limiter   │ ← Limits concurrent requests
└────────┬────────┘
         │
┌────────▼────────┐
│ Total Timeout   │ ← Overall operation timeout
└────────┬────────┘
         │
┌────────▼────────┐
│ Retry Policy    │ ← Automatic retry logic
└────────┬────────┘
         │
┌────────▼────────┐
│Circuit Breaker  │ ← Prevents cascading failures
└────────┬────────┘
         │
┌────────▼────────┐
│Attempt Timeout  │ ← Individual request timeout
└────────┬────────┘
         │
         ▼
    HTTP Request
```

This ordering is intentional:
1. **Rate Limiter** ensures we don't overload the system
2. **Total Timeout** sets the overall deadline
3. **Retry** attempts failed requests
4. **Circuit Breaker** stops requests to failing services
5. **Attempt Timeout** limits each individual attempt

## Best Practices and Recommendations

Based on our demo application, here are some key takeaways:

### 1. Configure Timeouts Appropriately

- **Attempt Timeout** should be less than your expected response time under normal conditions
- **Total Timeout** should account for maximum retries with backoff
- Example: 100ms attempt × 5 retries with exponential backoff ≈ 5 seconds total

### 2. Balance Retry Attempts

- Too few retries: Miss opportunities to recover from transient failures
- Too many retries: Waste resources and delay final failure detection
- 3-5 retries is typically a good balance

### 3. Use Jitter in Retry Delays

Always enable jitter to prevent synchronized retries:

```csharp
options.Retry.UseJitter = true;
```

This is especially important in distributed systems with many clients.

### 4. Tune Circuit Breaker Thresholds

The circuit breaker parameters depend on your application's requirements:

```csharp
// Conservative (tolerates more failures)
options.CircuitBreaker.FailureRatio = 0.9;  // 90% failure rate
options.CircuitBreaker.MinimumThroughput = 10;

// Aggressive (opens circuit quickly)
options.CircuitBreaker.FailureRatio = 0.5;  // 50% failure rate
options.CircuitBreaker.MinimumThroughput = 3;
```

### 5. Monitor Circuit Breaker State Changes

Always log circuit breaker state transitions:

```csharp
options.CircuitBreaker.OnOpened = args =>
{
    logger.LogWarning("Circuit breaker opened for {Service}", serviceName);
    // Optionally: Send alerts, update metrics, etc.
    return default;
};
```

This helps you detect and diagnose issues quickly.

### 6. Implement Proper Observability

Our custom colored logger provides visual feedback, but in production, you should also:

- Emit metrics (success rate, retry count, circuit breaker state)
- Use structured logging
- Integrate with monitoring systems (Prometheus, Application Insights, etc.)

### 7. Test Different Failure Scenarios

Use our demo's Blazor settings page approach to test various failure rates:

- **Normal operation**: 0-10% failures
- **Degraded service**: 20-40% failures
- **Service outage**: 70-100% failures

This helps you validate that your resilience configuration works as expected.

## Conclusion

Building resilient applications is essential in modern distributed systems. .NET's standard resilience handler provides a powerful, composable way to implement resilience patterns without writing boilerplate code.

In this article, we explored:

- **Rate Limiting**: Prevent overwhelming downstream services
- **Timeouts**: Set boundaries for operations and individual attempts
- **Retry Policies**: Automatically recover from transient failures
- **Circuit Breakers**: Prevent cascading failures and allow systems to recover

The demo application showed that even with 40% of requests experiencing delays or errors, the client operates seamlessly. At 70% failure rates, some requests fail but the system remains functional. Only when failures exceed 90% does the circuit breaker intervene to protect the system.

By understanding and properly configuring these resilience patterns, you can build applications that gracefully handle failures, maintain good user experience, and protect your systems from cascading failures.

## Further Reading

- [Microsoft.Extensions.Http.Resilience Documentation](https://learn.microsoft.com/en-us/dotnet/core/resilience/)
- [Polly Documentation](https://www.pollydocs.org/)
- [Cloud Design Patterns: Retry](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Cloud Design Patterns: Circuit Breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)

## Try It Yourself

Clone the repository and experiment with different configurations:

```bash
git clone https://github.com/SupaaHiro/schwifty-lab.git
cd schwifty-lab/projects/api-resilience
```

Try these experiments:

1. **Experiment with timeout values**: What happens if `AttemptTimeout` is longer than `DelayDurationMs`?
2. **Modify circuit breaker thresholds**: How does a lower `FailureRatio` affect behavior?
3. **Adjust retry attempts**: Compare the difference between 3 and 10 retry attempts
4. **Remove resilience patterns**: Comment out the resilience handler and observe the difference

Happy coding, and may your applications be ever resilient!
