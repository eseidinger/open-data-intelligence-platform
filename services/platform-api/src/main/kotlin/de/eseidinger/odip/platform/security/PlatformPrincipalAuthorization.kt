package de.eseidinger.odip.platform.security

import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.context.annotation.Configuration
import org.springframework.stereotype.Component
import org.springframework.web.servlet.HandlerInterceptor

@ConfigurationProperties("odip.authorization")
data class PlatformAuthorizationProperties(
    val requirePrincipalContext: Boolean = true,
    val strictPrincipalFormat: Boolean = true,
)

@Configuration
@EnableConfigurationProperties(PlatformAuthorizationProperties::class)
class PlatformAuthorizationConfiguration

@Component
class PlatformPrincipalAuthorizationInterceptor(
    private val properties: PlatformAuthorizationProperties,
) : HandlerInterceptor {
    override fun preHandle(request: HttpServletRequest, response: HttpServletResponse, handler: Any): Boolean {
        if (!request.requestURI.startsWith("/api/")) {
            return true
        }

        if (!properties.requirePrincipalContext) {
            return true
        }

        if (!hasValidPrincipalContext(request)) {
            response.status = 401
            response.contentType = "application/json"
            response.writer.write("""{"schemaVersion":"error/v1","status":401,"code":"unauthorized","message":"A valid trusted principal context is required"}""")
            return false
        }

        // All routes, including legacy routes, are authorized at the platform
        // boundary. Here we validate trusted context; domain services enforce
        // dataset grants, ownership, and claim tokens independently of groups.
        return true
    }

    private fun hasValidPrincipalContext(request: HttpServletRequest): Boolean {
        val names = listOf("Id","Kind","Issuer","Subject","Group-Ids") + if (request.getHeader("X-Platform-Principal-Kind") == "service") listOf("Client-Id") else emptyList()
        if (names.any { request.getHeaders("X-Platform-Principal-$it").toList().size != 1 }) return false
        if (listOf("Id","Issuer","Subject").any { request.getHeader("X-Platform-Principal-$it").isNullOrBlank() }) return false
        if (request.getHeader("X-Platform-Principal-Kind") !in setOf("user","service")) return false
        if (request.getHeader("X-Platform-Principal-Kind") == "service" && request.getHeader("X-Platform-Principal-Client-Id").isNullOrBlank()) return false
        if (!properties.strictPrincipalFormat) return true
        return Regex("^prn_[0-9a-f]{32}$").matches(request.getHeader("X-Platform-Principal-Id")) &&
            Regex("^grp_[0-9a-f]{32}( grp_[0-9a-f]{32})*$").matches(request.getHeader("X-Platform-Principal-Group-Ids")) &&
            Regex("^https://[^ ]+$").matches(request.getHeader("X-Platform-Principal-Issuer")) &&
            listOf("Subject").plus(if (request.getHeader("X-Platform-Principal-Kind") == "service") listOf("Client-Id") else emptyList())
                .all { request.getHeader("X-Platform-Principal-$it").length <= 200 && Regex("^[!-~]+$").matches(request.getHeader("X-Platform-Principal-$it")) }
    }
}
