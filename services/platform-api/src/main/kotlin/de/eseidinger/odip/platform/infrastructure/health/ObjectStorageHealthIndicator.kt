package de.eseidinger.odip.platform.infrastructure.health

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import org.springframework.beans.factory.annotation.Value
import org.springframework.boot.health.contributor.AbstractHealthIndicator
import org.springframework.boot.health.contributor.Health
import org.springframework.stereotype.Component

@Component
class ObjectStorageHealthIndicator(
    @Value("\${odip.object-storage.health-url}") private val healthUrl: URI,
) : AbstractHealthIndicator() {

    private val client = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(2))
        .build()

    override fun doHealthCheck(builder: Health.Builder) {
        val request = HttpRequest.newBuilder(healthUrl)
            .GET()
            .timeout(Duration.ofSeconds(2))
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.discarding())

        check(response.statusCode() in 200..299) {
            "Object storage responded with HTTP ${response.statusCode()}"
        }

        builder.up()
            .withDetail("endpoint", healthUrl.toString())
            .withDetail("status", response.statusCode())
    }
}
