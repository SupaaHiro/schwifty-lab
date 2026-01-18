using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using System.Diagnostics;
using static System.Net.WebRequestMethods;

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
      // Note: In this demo, all exceptions are treated as internal server errors (500).
      // In a real-world application, you would have more sophisticated logic to determine the appropriate status code, 
      // possibly based on custom exception types or other criteria.
      
      var problemDetails = new ProblemDetails
      {
        Status = StatusCodes.Status500InternalServerError,
        Title = "Internal Server Error",
        Detail = exception.Message,
        Instance = $"{httpContext.Request.Method} {httpContext.Request.Path}"
      };

      httpContext.Response.StatusCode = (int)problemDetails.Status;
      await httpContext.Response.WriteAsJsonAsync(problemDetails, cancellationToken);

      _logger.LogError("Err ({statusCode}) - {Message} ", httpContext.Response.StatusCode, exception.Message);

      return true;

    }
    catch (OperationCanceledException) { return true; }
  }
}