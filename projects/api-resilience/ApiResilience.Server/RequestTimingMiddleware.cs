using System.Diagnostics;

namespace ApiResilience.Server;

public sealed class RequestTimingMiddleware(RequestDelegate next, ILogger<RequestTimingMiddleware> logger)
{
  private readonly RequestDelegate _next = next;
  private readonly ILogger<RequestTimingMiddleware> _logger = logger;

  public async Task InvokeAsync(HttpContext context)
  {
    Stopwatch stopwatch = Stopwatch.StartNew();

    try
    {
      await _next(context);
    }
    finally
    {
      stopwatch.Stop();

      var statusCode = context.Response.StatusCode;
      var duration = stopwatch.ElapsedMilliseconds;
      if (statusCode >= 200 && statusCode < 300)
      {
        if (duration >= 1_000)
          _logger.LogWarning("{statusCode} (OK): {duration}ms", statusCode, duration);
        else
          _logger.LogInformation("{statusCode} (OK): {duration}ms", statusCode, duration);
      }
      else if (statusCode >= 400)
      {
        _logger.LogError("Err ({statusCode}): {duration}ms", statusCode, duration);
      }
    }
  }
}