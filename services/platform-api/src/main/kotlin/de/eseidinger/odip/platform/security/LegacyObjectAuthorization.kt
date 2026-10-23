package de.eseidinger.odip.platform.security

import de.eseidinger.odip.platform.publication.DatasetAccess
import de.eseidinger.odip.platform.publication.reject
import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Component
import org.springframework.web.servlet.HandlerInterceptor
import java.util.UUID

@Component
class LegacyObjectAuthorization(private val access: DatasetAccess, private val jdbc: JdbcTemplate) : HandlerInterceptor {
    override fun preHandle(request: HttpServletRequest, response: HttpServletResponse, handler: Any): Boolean {
        val path = request.requestURI.split('/').filter { it.isNotBlank() }
        if (path.size < 3 || path[1] == "v1") return true
        val id = runCatching { UUID.fromString(path[2]) }.getOrNull() ?: return true
        val permission = if (request.method in setOf("GET", "HEAD")) {
            "READ"
        } else if (path[1] in setOf("data-sources", "pipeline-runs")) {
            "INGEST"
        } else {
            "WRITE"
        }
        val datasets = when (path[1]) {
            "datasets" -> listOf(id)
            "raw-artifacts" -> jdbc.queryForList("SELECT ds.dataset_id FROM dataset_source ds JOIN raw_artifact a ON a.source_id=ds.source_id WHERE a.id=?", UUID::class.java, id)
            "pipeline-runs" -> jdbc.queryForList("SELECT ds.dataset_id FROM dataset_source ds JOIN pipeline_run r ON r.source_id=ds.source_id WHERE r.id=?", UUID::class.java, id)
            "data-sources" -> jdbc.queryForList("SELECT dataset_id FROM dataset_source WHERE source_id=?", UUID::class.java, id)
            else -> return true
        }
        val principal = access.principal(request)
        if (datasets.isNotEmpty() && datasets.filterNotNull().none { access.allowed(principal, it, permission) }) reject(403, "forbidden", "Dataset permission is required")
        if (datasets.isEmpty() && !access.developmentBypass()) reject(403, "forbidden", "A contributing dataset permission is required")
        return true
    }
}
