using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;

namespace ApiResilience.Server;

public abstract class ResponseExceptionBase(string error, int statusCode = 500) : Exception(error)
{
    public int StatusCode { get; init; } = statusCode;
}

public sealed class ResponseInternalErrorException(string message) : ResponseExceptionBase(message)
{

}

public sealed class GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger) : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger = logger;

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(httpContext);
        ArgumentNullException.ThrowIfNull(exception);

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

            if (_logger.IsEnabled(LogLevel.Trace))
                _logger.LogTrace("  Handled {Exception} for request {Method} {Path}", exception.GetType().Name, httpContext.Request.Method, httpContext.Request.Path);

            return true;

        }
        catch (OperationCanceledException) { return true; }
    }
}