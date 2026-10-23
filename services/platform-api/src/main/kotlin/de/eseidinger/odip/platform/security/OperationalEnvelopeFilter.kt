package de.eseidinger.odip.platform.security

import jakarta.servlet.FilterChain
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.MDC
import org.springframework.core.Ordered
import org.springframework.core.annotation.Order
import org.springframework.stereotype.Component
import org.springframework.web.filter.OncePerRequestFilter
import java.util.UUID

@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
class OperationalEnvelopeFilter : OncePerRequestFilter() {
    override fun doFilterInternal(request: HttpServletRequest, response: HttpServletResponse, chain: FilterChain) {
        if (!request.requestURI.startsWith("/api/")) {
            chain.doFilter(request, response)
            return
        }
        val supplied = request.getHeader("X-Correlation-Id").orEmpty()
        val correlation = if (Regex("^(?:[a-f0-9]{32}|[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12})$").matches(supplied)) supplied else UUID.randomUUID().toString()
        request.setAttribute("odip.correlationId", correlation)
        response.setHeader("X-Correlation-Id", correlation)
        val previousCorrelation = MDC.get("correlationId")
        MDC.put("correlationId", correlation)
        val startedAt = System.nanoTime()
        var failed = false
        try {
            chain.doFilter(request, response)
        } catch (error: Exception) {
            failed = true
            throw error
        } finally {
            val event = if (failed || response.status >= 400) "request.failed" else "request.completed"
            val level = if (failed || response.status >= 500) {
                "error"
            } else if (response.status >= 400) {
                "warning"
            } else {
                "info"
            }
            val status = if (failed) 500 else response.status
            val durationMs = (System.nanoTime() - startedAt) / 1_000_000
            if (previousCorrelation == null) MDC.remove("correlationId") else MDC.put("correlationId", previousCorrelation)
            // The platform collector accepts raw minimized JSON, without log prefixes.
            println("""{"event":"$event","level":"$level","correlationId":"$correlation","status":$status,"durationMs":$durationMs}""")
        }
    }
}
