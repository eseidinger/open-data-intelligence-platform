package de.eseidinger.odip.platform.publication

import de.eseidinger.odip.platform.security.PlatformAuthorizationProperties
import jakarta.servlet.http.HttpServletRequest
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service
import java.util.UUID

@Service
class DatasetAccess(private val jdbc: JdbcTemplate, private val properties: PlatformAuthorizationProperties) {
    fun principal(request: HttpServletRequest): String = request.getHeader("X-Platform-Principal-Id")
        ?: if (!properties.requirePrincipalContext) "development" else reject(401, "unauthorized", "Trusted principal context is required")

    fun operator(request: HttpServletRequest): Boolean = !properties.requirePrincipalContext ||
        request.getHeader("X-Platform-Principal-Kind") == "user" &&
        request.getHeader("X-Platform-Principal-Group-Ids").orEmpty().split(Regex("\\s+")).any(properties.userGroupIds::contains)

    fun requireOperator(request: HttpServletRequest) {
        if (!operator(request)) reject(403, "forbidden", "An application operator is required")
    }

    fun allowed(principal: String, dataset: UUID, permission: String): Boolean =
        !properties.requirePrincipalContext || jdbc.queryForObject(
            "SELECT EXISTS(SELECT 1 FROM dataset_grant WHERE dataset_id=? AND principal_id=? AND permission=?)",
            Boolean::class.java, dataset, principal, permission) == true

    fun require(request: HttpServletRequest, dataset: UUID, permission: String) {
        if (!allowed(principal(request), dataset, permission)) reject(403, "forbidden", "Dataset permission is required")
    }

    fun grant(dataset: UUID, principal: String, permission: String) {
        checkPublication(principal.length in 1..200 && permission in setOf("READ", "WRITE", "INGEST", "VALIDATE"), "invalid_grant", "Grant principal or permission is invalid", 400)
        jdbc.update("INSERT INTO dataset_grant VALUES (?,?,?) ON CONFLICT DO NOTHING", dataset, principal, permission)
    }

    fun audit(principal: String, action: String, dataset: UUID? = null, publication: UUID? = null) {
        val context = org.springframework.web.context.request.RequestContextHolder.getRequestAttributes() as? org.springframework.web.context.request.ServletRequestAttributes
        val correlation = context?.request?.getAttribute("odip.correlationId") as? String
        jdbc.update("INSERT INTO publication_audit(id,principal_id,action,dataset_id,publication_id,correlation_id) VALUES (?,?,?,?,?,?)", UUID.randomUUID(), principal, action, dataset, publication, correlation)
    }
}
