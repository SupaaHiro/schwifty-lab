using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace ApiResilience.Server;

public sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
  private readonly ILogger<GlobalExceptionHandler> _logger = logger;

  public async ValueTask<bool> TryHandleAsync(
      HttpContext httpContext,
      Exception exception,
      CancellationToken cancellationToken)
  {
    try
    {
      _logger.LogError("Error: Status {StatusCode} - {Message}", StatusCodes.Status500InternalServerError, exception.Message);

      var problemDetails = new ProblemDetails
      {
        Status = StatusCodes.Status500InternalServerError,
        Title = "Internal Server Error",
        Detail = exception.Message,
        Instance = $"{httpContext.Request.Method} {httpContext.Request.Path}"
      };

      httpContext.Response.StatusCode = StatusCodes.Status500InternalServerError;
      await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

      return true;

    }
    catch (OperationCanceledException) { return true; }
  }
}