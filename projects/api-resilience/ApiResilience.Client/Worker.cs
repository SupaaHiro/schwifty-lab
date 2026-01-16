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
    while (!stoppingToken.IsCancellationRequested)
    {

      await ExecuteOneAsync(stoppingToken);
      await Task.Delay(1_000, stoppingToken);
    }
  }

  private async Task ExecuteOneAsync(CancellationToken cancellationToken)
  {
    Stopwatch stopwatch = Stopwatch.StartNew();
    try
    {
      _ = await client.GetWeatherForecastAsync(cancellationToken);
      stopwatch.Stop();

      var duration = stopwatch.ElapsedMilliseconds;
      if (duration >= 1_000)
        logger.LogWarning("200 (OK): {duration}ms", stopwatch.ElapsedMilliseconds);
      else
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
    catch (TaskCanceledException)
    {
      logger.LogError("Err (TaskCanceledException): {duration}ms", stopwatch.ElapsedMilliseconds);
    }
    catch (BrokenCircuitException)
    {
      logger.LogError("Err (BrokenCircuitException): {duration}ms", stopwatch.ElapsedMilliseconds);
    }
  }
}
