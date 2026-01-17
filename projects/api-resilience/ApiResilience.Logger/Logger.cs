using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Configuration;
using Microsoft.Extensions.Options;
using System.Collections.Concurrent;
using System.Runtime.Versioning;

namespace ApiResilience.Logger;

public sealed class ColorConsoleLoggerConfiguration
{
  public int EventId { get; set; }

  public Dictionary<LogLevel, ConsoleColor> LogLevelToColorMap { get; set; } = new()
  {
    [LogLevel.Information] = ConsoleColor.Green,
    [LogLevel.Warning] = ConsoleColor.Yellow,
    [LogLevel.Error] = ConsoleColor.Red,
  };

  public bool SimplifiedOutput { get; set; }
}

public sealed class ColorConsoleLogger(
    string name,
    Func<ColorConsoleLoggerConfiguration> getCurrentConfig) : ILogger
{
  public IDisposable? BeginScope<TState>(TState state) where TState : notnull => default!;

  public bool IsEnabled(LogLevel logLevel) =>
      getCurrentConfig().LogLevelToColorMap.ContainsKey(logLevel);

  public void Log<TState>(
      LogLevel logLevel,
      EventId eventId,
      TState state,
      Exception? exception,
      Func<TState, Exception?, string> formatter)
  {
    if (!IsEnabled(logLevel))
    {
      return;
    }

    ColorConsoleLoggerConfiguration config = getCurrentConfig();
    if (config.EventId == 0 || config.EventId == eventId.Id)
    {
      ConsoleColor originalColor = Console.ForegroundColor;
      if (!config.SimplifiedOutput)
      {
        Console.ForegroundColor = config.LogLevelToColorMap[logLevel];
        Console.WriteLine($"[{eventId.Id,2}: {logLevel,-12}]");

        Console.ForegroundColor = originalColor;
        Console.Write($"     {name} - ");
      }
      Console.ForegroundColor = config.LogLevelToColorMap[logLevel];
      Console.Write($"{formatter(state, exception)}");

      Console.ForegroundColor = originalColor;
      Console.WriteLine();
    }
  }
}

[UnsupportedOSPlatform("browser")]
[ProviderAlias("ColorConsole")]
public sealed class ColorConsoleLoggerProvider : ILoggerProvider
{
  private readonly IDisposable? _onChangeToken;
  private ColorConsoleLoggerConfiguration _currentConfig;
  private readonly ConcurrentDictionary<string, ColorConsoleLogger> _loggers =
      new(StringComparer.OrdinalIgnoreCase);

  public ColorConsoleLoggerProvider(
      IOptionsMonitor<ColorConsoleLoggerConfiguration> config)
  {
    _currentConfig = config.CurrentValue;
    _onChangeToken = config.OnChange(updatedConfig => _currentConfig = updatedConfig);
  }

  public ILogger CreateLogger(string categoryName) =>
      _loggers.GetOrAdd(categoryName, name => new ColorConsoleLogger(name, GetCurrentConfig));

  private ColorConsoleLoggerConfiguration GetCurrentConfig() => _currentConfig;

  public void Dispose()
  {
    _loggers.Clear();
    _onChangeToken?.Dispose();
  }
}

public static class ColorConsoleLoggerExtensions
{
  public static ILoggingBuilder AddColorConsoleLogger(this ILoggingBuilder builder)
  {
    builder.AddConfiguration();

    builder.Services.TryAddEnumerable(ServiceDescriptor.Singleton<ILoggerProvider, ColorConsoleLoggerProvider>());

    LoggerProviderOptions.RegisterProviderOptions<ColorConsoleLoggerConfiguration, ColorConsoleLoggerProvider>(builder.Services);

    return builder;
  }

  public static ILoggingBuilder AddColorConsoleLogger(this ILoggingBuilder builder, Action<ColorConsoleLoggerConfiguration> configure)
  {
    builder.AddColorConsoleLogger();
    builder.Services.Configure(configure);

    return builder;
  }
}