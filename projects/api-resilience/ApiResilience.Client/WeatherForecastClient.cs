using ApiResilience.Contracts;
using System.Net.Http.Json;

namespace ApiResilience.Client;

public class WeatherForecastClient(HttpClient httpClient)
{
  public async Task<IEnumerable<WeatherForecast>> GetWeatherForecastAsync(CancellationToken cancellationToken = default)
  {
    var forecast = await httpClient.GetFromJsonAsync<WeatherForecast[]>("/weatherforecast", cancellationToken);
    return forecast ?? [];
  }
}