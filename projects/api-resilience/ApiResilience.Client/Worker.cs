using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Polly.CircuitBreaker;
using Polly.Timeout;
using System.Diagnostics;
using System.Net.Sockets;

namespace ApiResilience.Client;

public sealed class Worker(ILogger<Worker> logger, WeatherForecastClient client) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        try
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                await ExecuteOneAsync(stoppingToken);
                await Task.Delay(1_000, stoppingToken);
            }
        }
        catch (TaskCanceledException)
        {
            logger.LogWarning("Worker is stopping due to cancellation.");
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
            if (logger.IsEnabled(LogLevel.Warning) && duration >= 1_000)
                logger.LogWarning("200 (OK): {duration}ms", stopwatch.ElapsedMilliseconds);
            else if (logger.IsEnabled(LogLevel.Information))
                logger.LogInformation("200 (OK): {duration}ms", stopwatch.ElapsedMilliseconds);
        }
        catch (HttpRequestException httpEx)
        {
            stopwatch.Stop();
            if (httpEx.StatusCode.HasValue && (int)httpEx.StatusCode.Value >= 500)
                logger.LogError("Err ({statusCode}): {duration}ms", (int)httpEx.StatusCode.Value, stopwatch.ElapsedMilliseconds);
            else if (httpEx.InnerException is SocketException socketException)
                logger.LogError("Err ({error}): {duration}ms", socketException.SocketErrorCode, stopwatch.ElapsedMilliseconds);
            else
                logger.LogError("Err ({error}): {duration}ms", (httpEx.InnerException ?? httpEx).GetType().Name, stopwatch.ElapsedMilliseconds);
        }
        catch (TimeoutRejectedException)
        {
            logger.LogError("Err (TimeoutRejectedException): {duration}ms", stopwatch.ElapsedMilliseconds);
        }
        catch (BrokenCircuitException)
        {
            logger.LogError("Err (BrokenCircuitException): {duration}ms", stopwatch.ElapsedMilliseconds);
        }
    }
}
