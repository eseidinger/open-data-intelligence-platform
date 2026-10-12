package de.eseidinger.odip.platform.security

import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.boot.context.properties.EnableConfigurationProperties
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpMethod
import org.springframework.stereotype.Component
import org.springframework.web.servlet.HandlerInterceptor

private const val GROUP_IDS_HEADER = "X-Platform-Principal-Group-Ids"

@ConfigurationProperties("odip.authorization")
data class PlatformAuthorizationProperties(
    val userGroupIds: Set<String> = emptySet(),
    val guestGroupIds: Set<String> = emptySet(),
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

        // The platform authenticates and authorizes v1 routes. DatasetAccess
        // enforces local object permissions; platform groups are not repeated here.
        if (request.requestURI.startsWith("/api/v1/")) return true
        if (request.getHeader("X-Platform-Principal-Kind") == "service" && request.requestURI.startsWith("/api/pipeline-runs/")) return true

        val groupIds = request.getHeader(GROUP_IDS_HEADER)
            ?.trim()
            ?.split(Regex("\\s+"))
            ?.filter(String::isNotBlank)
            ?.toSet()
            .orEmpty()
        val isUser = groupIds.any(properties.userGroupIds::contains)
        val isGuest = groupIds.any(properties.guestGroupIds::contains)

        if (isUser || isGuest && request.method in readOnlyMethods) {
            return true
        }

        response.status = 403
        response.contentType = "application/json"
        response.writer.write("""{"schemaVersion":"error/v1","status":403,"code":"forbidden","message":"The caller is not allowed to perform this operation"}""")
        return false
    }

    private companion object {
        val readOnlyMethods = setOf(HttpMethod.GET.name(), HttpMethod.HEAD.name(), HttpMethod.OPTIONS.name())
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
