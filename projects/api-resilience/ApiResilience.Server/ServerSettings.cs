using Microsoft.Extensions.Options;
using System.ComponentModel.DataAnnotations;

namespace ApiResilience.Server;

[ServerSettingsValidation]
public sealed class ServerSettings
{
    public const string SectionName = "Server";

    /// <summary>
    /// Warmup period in seconds before introducing random delays and errors
    /// </summary>
    [Range(0, 600, ErrorMessage = "WarmupSeconds must be between 0 and 600")]
    public int WarmupSeconds { get; set; } = 10;

    /// <summary>
    /// Probability (0.0 to 1.0) of introducing a delay in the API response
    /// </summary>
    [Range(0.0, 1.0, ErrorMessage = "DelayProbability must be between 0.0 and 1.0")]
    public double DelayProbability { get; set; } = 0.2;

    /// <summary>
    /// Delay duration in milliseconds when a delay is triggered
    /// </summary>
    [Range(0, 30_000, ErrorMessage = "DelayDurationMs must be between 0 and 30000")]
    public int DelayDurationMs { get; set; } = 5_000;

    /// <summary>
    /// Probability (0.0 to 1.0) of throwing an error in the API response
    /// </summary>
    [Range(0.0, 1.0, ErrorMessage = "ErrorProbability must be between 0.0 and 1.0")]
    public double ErrorProbability { get; set; } = 0.2;
}

[AttributeUsage(AttributeTargets.Class)]
public sealed class ServerSettingsValidationAttribute : ValidationAttribute
{
    protected override ValidationResult? IsValid(object? value, ValidationContext validationContext)
    {
        if (value is not ServerSettings settings)
            return new ValidationResult("Invalid object type");

        if (settings.DelayProbability + settings.ErrorProbability > 1.0)
        {
            return new ValidationResult(
                "The sum of DelayProbability and ErrorProbability cannot exceed 1.0 (100%)",
                [nameof(ServerSettings.DelayProbability), nameof(ServerSettings.ErrorProbability)]
            );
        }

        return ValidationResult.Success;
    }
}

public sealed class ServerSettingsService
{
    private ServerSettings _settings;

    public ServerSettingsService(IOptionsMonitor<ServerSettings> options)
    {
        ArgumentNullException.ThrowIfNull(options);

        _settings = options.CurrentValue;
        options.OnChange(newSettings => _settings = newSettings);
    }

    public ServerSettings GetCurrentSettings() => new()
    {
        WarmupSeconds = _settings.WarmupSeconds,
        DelayProbability = _settings.DelayProbability,
        DelayDurationMs = _settings.DelayDurationMs,
        ErrorProbability = _settings.ErrorProbability
    };

    public void UpdateSettings(ServerSettings newSettings)
    {
        ArgumentNullException.ThrowIfNull(newSettings);

        _settings.WarmupSeconds = newSettings.WarmupSeconds;
        _settings.DelayProbability = newSettings.DelayProbability;
        _settings.DelayDurationMs = newSettings.DelayDurationMs;
        _settings.ErrorProbability = newSettings.ErrorProbability;
    }

    public ServerSettings GetRuntimeSettings() => _settings;
}