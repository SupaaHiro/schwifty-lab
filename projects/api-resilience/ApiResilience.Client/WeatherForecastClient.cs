using System.Net.Http.Json;
using ApiResilience.Contracts;

namespace ApiResilience.Client;

public class WeatherForecastClient(HttpClient httpClient)
{
  public async Task<IEnumerable<WeatherForecast>> GetWeatherForecastAsync(CancellationToken cancellationToken = default)
  {
    var forecast = await httpClient.GetFromJsonAsync<WeatherForecast[]>("/weatherforecast", cancellationToken);
    return forecast ?? [];
  }
}